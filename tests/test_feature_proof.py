"""
Tests for the "feature proof" additions: KYC completeness, the tamper-evident
hash-chained audit log, cross-case network insights, and live transaction
intake. Each borrows a concept from two prior hackathon projects (KYC
cross-checks, hash-chained audit, shared-entity/network detection) adapted to
this project's actual domain — see aci/agents/kyc_agent.py, aci/db.py, and
aci/api/app.py module docstrings for what was kept vs. deliberately not
reimplemented (OCR/biometrics, a graph database, post-quantum crypto).
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from aci import config, db
from aci.agents import kyc_agent
from aci.data.synthetic import seed_world
from aci.models import Customer, Entity, Severity
from aci.orchestrator import investigate
from aci.rules_catalog import catalog as rules_catalog


# ── KYC completeness agent ──────────────────────────────────────────────────

def test_kyc_clean_record_is_complete():
    world = seed_world()
    r = kyc_agent.run("CASE-X", world.transactions["TX-84721"], world)
    assert r.dimension == "kyc"
    assert r.extra["complete"] is True
    assert r.findings == []


def test_kyc_missing_entity_link_flagged():
    world = seed_world()
    world.customers["C-GHOST"] = Customer(customer_id="C-GHOST", name="Ghost Corp", country="India",
                                          industry="x", onboarded="2020-01-01")
    txn = world.transactions["TX-84721"].model_copy(update={"customer_id": "C-GHOST"})
    r = kyc_agent.run("CASE-X", txn, world)
    assert any(f.type == "kyc_missing_ownership" for f in r.findings)
    assert r.extra["complete"] is False


def test_kyc_date_inconsistency_flagged():
    world = seed_world()
    world.customers["C-TIME"] = Customer(customer_id="C-TIME", name="Time Corp", country="India",
                                         industry="x", onboarded="2020-01-01", entity_id="E-TIME")
    world.entities["E-TIME"] = Entity(entity_id="E-TIME", name="Time Corp", entity_type="company",
                                      country="India", registered="2025-01-01", directors=["P-X"])
    txn = world.transactions["TX-84721"].model_copy(update={"customer_id": "C-TIME"})
    r = kyc_agent.run("CASE-X", txn, world)
    assert any(f.type == "kyc_date_inconsistency" for f in r.findings)


def test_kyc_never_enters_risk_score():
    """KYC is a data-quality check, not a risk-scoring dimension — it must
    never silently become a 7th weight."""
    assert "kyc" not in config.RISK_WEIGHTS
    world = seed_world()
    case = investigate("TX-84721", world, use_ai_narrative=False)
    assert {r.key for r in case.risk.rows} == set(config.RISK_WEIGHTS)
    assert any(r.dimension == "kyc" for r in case.agent_results)  # still runs and is reported


# ── Tamper-evident hash-chained audit log ───────────────────────────────────

def test_audit_chain_verifies_clean(tmp_path):
    db_path = tmp_path / "aci.db"
    db.init_db(db_path)
    world = seed_world()
    case = investigate("TX-84721", world, use_ai_narrative=False)
    db.save_case(case, db_path)

    result = db.verify_audit_chain(case.case_id, db_path)
    assert result["verified"] is True
    assert result["entries"] == len(case.audit)
    assert result["broken_at"] is None


def test_audit_chain_detects_tampering(tmp_path):
    import sqlite3
    db_path = tmp_path / "aci.db"
    db.init_db(db_path)
    world = seed_world()
    case = investigate("TX-84721", world, use_ai_narrative=False)
    db.save_case(case, db_path)

    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "UPDATE audit_log SET action = 'TAMPERED' WHERE case_id = ? AND audit_id = "
        "(SELECT MIN(audit_id) FROM audit_log WHERE case_id = ?)", (case.case_id, case.case_id))
    conn.commit()
    conn.close()

    result = db.verify_audit_chain(case.case_id, db_path)
    assert result["verified"] is False
    assert result["broken_at"] is not None


def test_audit_chain_grows_correctly_across_multiple_saves(tmp_path):
    """save_case() is called more than once as a case progresses (create,
    then each human decision) — the chain must extend correctly each time,
    not reset or duplicate."""
    from aci.orchestrator import record_human_decision
    db_path = tmp_path / "aci.db"
    db.init_db(db_path)
    world = seed_world()
    case = investigate("TX-84721", world, use_ai_narrative=False)
    db.save_case(case, db_path)
    n1 = db.verify_audit_chain(case.case_id, db_path)["entries"]

    case = record_human_decision(case, "officer", "close", role="officer")
    db.save_case(case, db_path)
    n2 = db.verify_audit_chain(case.case_id, db_path)

    assert n2["entries"] > n1
    assert n2["verified"] is True


# ── Cross-case network insights ─────────────────────────────────────────────

def test_network_insights_finds_entity_shared_across_customers(tmp_path):
    db_path = tmp_path / "aci.db"
    db.init_db(db_path)
    world = seed_world()
    # TX-84721 (C-1001) and TX-90233 (C-1003) both use beneficiary E-B.
    for tid in ("TX-84721", "TX-90233"):
        db.save_case(investigate(tid, world, use_ai_narrative=False), db_path)

    insights = db.network_insights(db_path)
    shared = next((i for i in insights if i["entity_id"] == "E-B"), None)
    assert shared is not None
    assert shared["customer_count"] == 2


def test_network_insights_empty_for_single_case(tmp_path):
    db_path = tmp_path / "aci.db"
    db.init_db(db_path)
    world = seed_world()
    db.save_case(investigate("TX-77310", world, use_ai_narrative=False), db_path)
    assert db.network_insights(db_path) == []


# ── Rules catalogue ──────────────────────────────────────────────────────────

def test_rules_catalog_is_nonempty_and_well_formed():
    rules = rules_catalog()
    assert len(rules) >= 10
    for r in rules:
        assert r["key"] and r["agent"] and r["category"] and r["trigger"]


# ── New-transaction intake (real HTTP, since this mutates shared process state) ──

def test_new_transaction_intake_is_immediately_investigable(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "aci.db")
    from aci.api.app import app
    db.init_db(config.DB_PATH)
    client = TestClient(app)

    resp = client.post("/api/transactions", json={
        "customer_id": "C-1001", "amount": 55_000_000,
        "beneficiary_name": "Judge Test Trading LLC", "beneficiary_country": "UAE",
        "destination_country": "UAE", "purpose": "Live demo submission",
        "document_narrative": "services", "document_amount": 55_000_000,
    })
    assert resp.status_code == 200
    tid = resp.json()["transaction_id"]

    inv = client.post("/api/investigations", json={"transaction_id": tid})
    assert inv.status_code == 200
    case = inv.json()
    signal_types = {s["type"] for r in case["agent_results"] for s in r.get("signals", [])}
    # A brand-new, large transaction to a beneficiary registered today should
    # genuinely trip amount_anomaly and new_counterparty — not staged data.
    assert "amount_anomaly" in signal_types
    assert "new_counterparty" in signal_types


def test_new_transaction_unknown_customer_rejected(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "aci.db")
    from aci.api.app import app
    client = TestClient(app)
    resp = client.post("/api/transactions", json={
        "customer_id": "C-NOPE", "amount": 1000, "beneficiary_name": "X",
        "beneficiary_country": "UAE", "destination_country": "UAE",
    })
    assert resp.status_code == 404


# ── Risk methodology / policy endpoint data integrity ───────────────────────

def test_risk_policy_covers_every_severity_band():
    for band in (Severity.NONE, Severity.LOW, Severity.MEDIUM, Severity.HIGH):
        assert band.value in config.RISK_POLICY
