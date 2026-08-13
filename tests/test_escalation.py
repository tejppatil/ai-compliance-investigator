"""
Two-tier escalation and Risk-Based Approach tests.

The escalation control (aci/orchestrator.py record_human_decision) is only
worth calling "real" if a tier-1 officer is actually rejected — server-side,
not just hidden behind a disabled button — when trying to re-decide a case
that's already escalated to the senior reviewer. That is the core claim
tested here, both at the orchestrator level and over the real HTTP API.
"""
from __future__ import annotations

import pytest

from aci import db
from aci.agents import risk_agent
from aci.data.synthetic import seed_world
from aci.models import AgentResult, Customer, Severity
from aci.orchestrator import investigate, record_human_decision


def _empty_results() -> dict[str, AgentResult]:
    return {dim: AgentResult(agent="x", case_id="C", dimension=dim, severity=Severity.NONE)
            for dim in ("transaction", "entity", "regulatory", "documentation")}


def _escalated_case():
    world = seed_world()
    case = investigate("TX-84721", world, use_ai_narrative=False)
    case = record_human_decision(case, "officer", "escalate", "UBO unverified", role="officer")
    return case


def test_escalate_assigns_senior_reviewer_with_sla():
    case = _escalated_case()
    assert case.escalation_level == 1
    assert case.status == "escalated"
    assert case.assigned_to and "Senior Compliance Officer" in case.assigned_to
    assert case.sla_due_at is not None


def test_officer_cannot_redecide_an_escalated_case():
    case = _escalated_case()
    with pytest.raises(PermissionError):
        record_human_decision(case, "officer", "close", role="officer")
    # Rejection must not corrupt state — still escalated, still assigned.
    assert case.escalation_level == 1
    assert case.status == "escalated"


def test_senior_close_approves_and_closes():
    case = _escalated_case()
    case = record_human_decision(case, "senior", "senior_close", "Reviewed, agree with HIGH", role="senior")
    assert case.status == "closed"
    assert any("approved" in a.action.lower() for a in case.audit if a.actor == "human")


def test_senior_override_closes_with_distinct_audit_wording():
    case = _escalated_case()
    case = record_human_decision(case, "senior", "senior_override", "Disagree, downgrading", role="senior")
    assert case.status == "closed"
    assert any("overrode" in a.action.lower() for a in case.audit if a.actor == "human")


def test_senior_return_resets_to_tier1():
    case = _escalated_case()
    case = record_human_decision(case, "senior", "senior_return", "Need more docs", role="senior")
    assert case.escalation_level == 0
    assert case.status == "pending_human_review"
    assert case.assigned_to is None
    assert case.sla_due_at is None
    # The officer can now act again — tier 1 is genuinely reopened.
    case = record_human_decision(case, "officer", "close", role="officer")
    assert case.status == "closed"


def test_senior_wrong_decision_vocabulary_on_escalated_case_rejected():
    case = _escalated_case()
    with pytest.raises(ValueError):
        record_human_decision(case, "senior", "close", role="senior")  # tier-1 word on a tier-2 case


def test_officer_wrong_decision_vocabulary_on_fresh_case_rejected():
    world = seed_world()
    case = investigate("TX-84721", world, use_ai_narrative=False)
    with pytest.raises(ValueError):
        record_human_decision(case, "officer", "senior_close", role="officer")  # tier-2 word on a tier-1 case


def test_either_persona_may_make_the_first_decision():
    """Tier 1 doesn't gate by role — either officer may make the initial
    call, matching how compliance teams actually triage (§13)."""
    world = seed_world()
    case = investigate("TX-84721", world, use_ai_narrative=False)
    case = record_human_decision(case, "senior", "edd", role="senior")
    assert case.status == "in_review"


# ── DB persistence & migration ──────────────────────────────────────────────

def test_escalation_fields_persist_across_save_and_reload(tmp_path):
    db_path = tmp_path / "aci.db"
    db.init_db(db_path)
    case = _escalated_case()
    db.save_case(case, db_path)

    reloaded = db.get_case(case.case_id, db_path)
    assert reloaded.escalation_level == 1
    assert reloaded.assigned_to == case.assigned_to
    assert reloaded.sla_due_at is not None


def test_list_escalations_reflects_state_and_clears_on_resolution(tmp_path):
    db_path = tmp_path / "aci.db"
    db.init_db(db_path)
    case = _escalated_case()
    db.save_case(case, db_path)

    open_escalations = db.list_escalations(db_path)
    assert any(e["case_id"] == case.case_id for e in open_escalations)

    resolved = record_human_decision(case, "senior", "senior_close", role="senior")
    db.save_case(resolved, db_path)
    still_open = db.list_escalations(db_path)
    assert not any(e["case_id"] == case.case_id for e in still_open)


def test_db_migrates_a_pre_escalation_schema_in_place(tmp_path):
    """A database created before this feature (no escalation columns) must
    upgrade in place on next connection, not require a wipe."""
    import sqlite3
    old_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(str(old_path))
    conn.executescript("""
        CREATE TABLE investigation_case (
            case_id TEXT PRIMARY KEY, transaction_id TEXT NOT NULL, priority TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending_human_review', created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL, case_json TEXT NOT NULL
        );
        CREATE TABLE audit_log (
            audit_id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL,
            actor TEXT NOT NULL, action TEXT NOT NULL, ts TEXT NOT NULL, details TEXT
        );
    """)
    conn.commit()
    conn.close()

    case = _escalated_case()
    db.save_case(case, old_path)  # must not raise despite the pre-migration schema
    reloaded = db.get_case(case.case_id, old_path)
    assert reloaded.escalation_level == 1


# ── API-level enforcement (the real HTTP boundary, not just the function) ──

def test_api_rejects_tier1_redecision_with_real_403(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from aci import config
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "aci.db")
    from aci.api.app import app
    db.init_db(config.DB_PATH)

    client = TestClient(app)
    created = client.post("/api/investigations", json={"transaction_id": "TX-84721"}).json()
    case_id = created["case_id"]

    esc = client.post(f"/api/investigations/{case_id}/review",
                      json={"decision": "escalate", "note": "test", "role": "officer"})
    assert esc.status_code == 200
    assert esc.json()["escalation_level"] == 1

    blocked = client.post(f"/api/investigations/{case_id}/review",
                          json={"decision": "close", "role": "officer"})
    assert blocked.status_code == 403

    resolved = client.post(f"/api/investigations/{case_id}/review",
                           json={"decision": "senior_close", "role": "senior"})
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "closed"

    queue = client.get("/api/escalations").json()
    assert not any(e["case_id"] == case_id for e in queue)


# ── Risk-Based Approach: the customer_risk dimension ────────────────────────

def _customer(risk_profile: str) -> Customer:
    return Customer(customer_id="C-TEST", name="Test Co", country="India", industry="general",
                    onboarded="2020-01-01", risk_profile=risk_profile)


def test_high_risk_customer_produces_high_customer_risk_row():
    world = seed_world()
    txn = world.transactions["TX-77310"]  # otherwise-normal transaction
    risk = risk_agent.run("CASE-X", txn, _empty_results(), _customer("high"))
    row = next(r for r in risk.rows if r.key == "customer_risk")
    assert row.severity == Severity.HIGH
    assert "high" in row.source_refs[0]


def test_unrecognized_risk_profile_falls_back_to_standard_not_crash():
    world = seed_world()
    txn = world.transactions["TX-77310"]
    risk = risk_agent.run("CASE-X", txn, _empty_results(), _customer("some_typo_value"))
    row = next(r for r in risk.rows if r.key == "customer_risk")
    assert row.severity == Severity.LOW  # "standard" fallback


def test_customer_risk_only_case_still_flags_via_regulatory_edd():
    """TX-31204: nothing about the transaction's own behaviour is anomalous —
    transaction/entity/documentation must all be NONE — yet the customer's
    persistent HIGH risk rating still shows up as HIGH and pulls in the
    FATF R.1 enhanced-due-diligence citation. That's the RBA claim: risk can
    come from who the customer is, not only from what this transaction did."""
    world = seed_world()
    case = investigate("TX-31204", world, use_ai_narrative=False)
    rows = {r.key: r for r in case.risk.rows}
    assert rows["transaction"].severity == Severity.NONE
    assert rows["entity"].severity == Severity.NONE
    assert rows["documentation"].severity == Severity.NONE
    assert rows["customer_risk"].severity == Severity.HIGH
    reg = next(r for r in case.agent_results if r.dimension == "regulatory")
    assert any(h.id == "FATF-R1" for h in reg.regulatory)
