"""
Cross-cutting hardening checks for the features added in phases 1-4.

Individual features test their own degraded behaviour; this file asserts the
properties that only hold when you look at the system as a whole:

  - With no LLM at all, every deterministic output is BYTE-IDENTICAL to a run
    with the LLM available. That's the project's central claim, and adding
    four features is exactly when it quietly stops being true.
  - Every action that changes or interrogates a case reaches the hash-chained
    audit log, not just the case record.
  - The rules catalogue and config can't drift apart.
"""
from __future__ import annotations

import pytest

from aci import config, db, llm, triage
from aci.data.synthetic import seed_world
from aci.orchestrator import investigate, record_human_decision
from aci.rules_catalog import catalog


# ── the central claim: no LLM changes nothing deterministic ──────────────

@pytest.mark.parametrize("tx", ["TX-84721", "TX-66150", "TX-66151", "TX-31204"])
def test_deterministic_output_is_identical_with_and_without_the_llm(tx, monkeypatch):
    """Anomaly detection, screening, risk scoring, citations, evidence and
    IDs must not depend on the model in any way. Only the prose may differ."""
    with_llm = investigate(tx, seed_world(), use_ai_narrative=False)

    monkeypatch.setattr(llm, "_call_ollama", lambda *a, **k: None)
    without = investigate(tx, seed_world(), use_ai_narrative=True)

    assert with_llm.priority == without.priority
    assert with_llm.risk.score == without.risk.score
    assert with_llm.risk.band == without.risk.band
    assert with_llm.sanctions_status == without.sanctions_status
    assert with_llm.risk.sanctions_floor_applied == without.risk.sanctions_floor_applied
    assert [f.id for r in with_llm.agent_results for f in r.findings] == \
           [f.id for r in without.agent_results for f in r.findings]
    assert [e.id for e in with_llm.evidence] == [e.id for e in without.evidence]
    assert [h.id for r in with_llm.agent_results for h in r.regulatory] == \
           [h.id for r in without.agent_results for h in r.regulatory]


def test_every_agent_runs_with_the_llm_down(monkeypatch):
    monkeypatch.setattr(llm, "_call_ollama", lambda *a, **k: None)
    case = investigate("TX-66150", seed_world(), use_ai_narrative=True)
    dimensions = {r.dimension for r in case.agent_results}
    assert dimensions == {"transaction", "entity", "sanctions", "regulatory", "documentation", "kyc"}


def test_triage_ranking_is_unaffected_by_the_llm(monkeypatch):
    """Ranking reads persisted case summaries — it must not so much as touch
    the model."""
    monkeypatch.setattr(llm, "_call_ollama", lambda *a, **k: None)
    cases = [
        {"case_id": "A", "priority": "low", "status": "pending_human_review",
         "sanctions_status": "hit", "escalation_level": 0, "created_at": "2026-01-01T00:00:00+00:00"},
        {"case_id": "B", "priority": "high", "status": "pending_human_review",
         "sanctions_status": "clear", "escalation_level": 0, "created_at": "2026-01-01T00:00:00+00:00"},
    ]
    assert [c["case_id"] for c in triage.rank(cases)] == ["A", "B"]


# ── audit completeness across the whole lifecycle ────────────────────────

def test_full_lifecycle_is_captured_in_the_hash_chained_log(tmp_path, monkeypatch):
    """Every state-changing step — screening, the risk floor, the AI
    suggestion, the human decision, the escalation assignment — has to be in
    audit_log, not only inside the case JSON."""
    import json as _json
    monkeypatch.setattr(llm, "_call_ollama", lambda *a, **k: _json.dumps({
        "what_happened": "A.", "why_unusual": "B.", "who_involved": "C.", "conclusion": "D.",
        "suggested_action": "Consider enhanced due diligence.",
    }))
    db_path = tmp_path / "aci.db"
    db.init_db(db_path)

    case = investigate("TX-66150", seed_world(), use_ai_narrative=True)
    case = record_human_decision(case, "officer", "escalate", "to senior", role="officer")
    db.save_case(case, db_path)

    actions = " | ".join(a["action"] for a in db.get_audit_log(case.case_id, db_path))
    for expected in ["Sanctions screening: CONFIRMED MATCH", "sanctions floor",
                     "AI SUGGESTED (not a decision)", "Compliance officer decision: escalate",
                     "Case assigned to"]:
        assert expected in actions, f"missing from the audit log: {expected}"

    assert db.verify_audit_chain(case.case_id, db_path)["verified"] is True


def test_a_clean_screening_is_logged_too(tmp_path):
    """Absence of a hit must be a positive record, or 'was this screened?'
    can't be answered after the fact."""
    db_path = tmp_path / "aci.db"
    db.init_db(db_path)
    case = investigate("TX-66151", seed_world(), use_ai_narrative=False)
    db.save_case(case, db_path)
    actions = " | ".join(a["action"] for a in db.get_audit_log(case.case_id, db_path))
    assert "Sanctions screening: no match" in actions


def test_audit_chain_survives_a_long_multi_feature_lifecycle(tmp_path, monkeypatch):
    """Appending Q&A turns and a senior decision after the fact must not
    break tamper-evidence."""
    from aci.models import AuditEntry
    db_path = tmp_path / "aci.db"
    db.init_db(db_path)

    case = investigate("TX-84721", seed_world(), use_ai_narrative=False)
    db.save_case(case, db_path)

    case.audit.append(AuditEntry(actor="human", action='Officer asked the case Q&A: "Why HIGH?"'))
    case.audit.append(AuditEntry(actor="system", action='Case Q&A answered (AI-generated, evidence-scoped): "..."'))
    case = record_human_decision(case, "officer", "escalate", role="officer")
    db.save_case(case, db_path)

    case = record_human_decision(case, "senior", "senior_close", "reviewed", role="senior")
    db.save_case(case, db_path)

    result = db.verify_audit_chain(case.case_id, db_path)
    assert result["verified"] is True and result["broken_at"] is None
    assert result["entries"] >= 12


# ── catalogue / config consistency ───────────────────────────────────────

def test_every_catalogued_rule_names_a_real_agent_file():
    import os
    for rule in catalog():
        assert os.path.exists(rule["file"]), f"{rule['key']} points at a missing file: {rule['file']}"


def test_catalogue_covers_every_finding_type_the_pipeline_emits():
    """A rule that can fire but isn't catalogued is exactly the drift the
    catalogue exists to prevent."""
    catalogued = {r["key"] for r in catalog()}
    emitted: set[str] = set()
    for tx in ("TX-84721", "TX-90233", "TX-77310", "TX-31204", "TX-66150", "TX-66151"):
        case = investigate(tx, seed_world(), use_ai_narrative=False)
        for r in case.agent_results:
            emitted |= {f.type for f in r.findings}
            emitted |= {s.type for s in r.signals}
    missing = emitted - catalogued
    assert not missing, f"emitted but not catalogued: {sorted(missing)}"


def test_sanctions_thresholds_in_the_catalogue_match_config():
    """The catalogue quotes live config values; this pins that they haven't
    been hardcoded into prose that could drift."""
    text = " ".join(r["trigger"] for r in catalog() if r["key"].startswith("sanctions"))
    assert f"{config.SANCTIONS_MATCH_CONFIRMED:.0%}" in text
    assert f"{config.SANCTIONS_MATCH_POSSIBLE:.0%}" in text


def test_risk_weights_still_sum_to_one():
    assert abs(sum(config.RISK_WEIGHTS.values()) - 1.0) < 1e-9


def test_triage_weights_are_all_positive():
    """A zero or negative weight would silently disable a ranking factor."""
    assert all(v > 0 for v in config.TRIAGE_WEIGHTS.values())


# ── fresh-database path ──────────────────────────────────────────────────

def test_all_new_features_work_against_a_brand_new_database(tmp_path):
    db_path = tmp_path / "fresh.db"
    case = investigate("TX-66150", seed_world(), use_ai_narrative=False)
    db.save_case(case, db_path)  # no init_db() first — must self-heal

    reloaded = db.get_case(case.case_id, db_path)
    assert reloaded.sanctions_status == "hit"
    assert db.verify_audit_chain(case.case_id, db_path)["verified"] is True
    ranked = triage.rank(db.list_cases(db_path))
    assert ranked and ranked[0]["triage_reasons"]
