"""
AI-drafted "suggested action" tests.

The whole risk of this feature is drift: a suggestion that quietly becomes a
default, a default that quietly becomes the recorded outcome. These tests pin
the boundary — the suggestion is generated, labelled, and audit-logged, and
it can never reach the case's disposition unless a human explicitly submits
it as their own decision.
"""
from __future__ import annotations

import pytest

from aci import llm
from aci.data.synthetic import seed_world
from aci.models import Narrative, Severity
from aci.orchestrator import investigate, record_human_decision


def _model_available() -> bool:
    s = llm.ollama_status()
    return bool(s.get("available") and s.get("llm_model_pulled"))


requires_model = pytest.mark.skipif(not _model_available(), reason="local LLM not running")


# ── it must never be fabricated ──────────────────────────────────────────

def test_template_narrative_has_no_suggestion():
    """The deterministic path must OMIT the suggestion rather than invent a
    generic one — a made-up recommendation is worse than none."""
    world = seed_world()
    case = investigate("TX-84721", world, use_ai_narrative=False)
    assert case.narrative.source == "template"
    assert case.narrative.suggested_action is None


def test_no_ollama_yields_no_suggestion(monkeypatch):
    monkeypatch.setattr(llm, "_call_ollama", lambda *a, **k: None)
    world = seed_world()
    case = investigate("TX-84721", world, use_ai_narrative=True)
    assert case.narrative.source == "template"
    assert case.narrative.suggested_action is None


def test_model_reply_without_the_field_still_yields_a_valid_narrative(monkeypatch):
    """suggested_action is optional on purpose: a model that omits it should
    cost us the suggestion, not the entire narrative."""
    import json as _json
    monkeypatch.setattr(llm, "_call_ollama", lambda *a, **k: _json.dumps({
        "what_happened": "A.", "why_unusual": "B.", "who_involved": "C.", "conclusion": "D.",
    }))
    world = seed_world()
    case = investigate("TX-84721", world, use_ai_narrative=True)
    assert case.narrative.source == "ai"
    assert case.narrative.suggested_action is None


def test_blank_suggestion_is_normalised_to_none(monkeypatch):
    import json as _json
    monkeypatch.setattr(llm, "_call_ollama", lambda *a, **k: _json.dumps({
        "what_happened": "A.", "why_unusual": "B.", "who_involved": "C.", "conclusion": "D.",
        "suggested_action": "   ",
    }))
    case = investigate("TX-84721", seed_world(), use_ai_narrative=True)
    assert case.narrative.suggested_action is None


# ── it must never become the decision ────────────────────────────────────

def test_suggestion_does_not_set_the_case_outcome():
    """A case carrying a suggestion is still awaiting a human — the presence
    of advice must not advance the state machine."""
    world = seed_world()
    case = investigate("TX-84721", world, use_ai_narrative=False)
    case.narrative = Narrative(source="ai", what_happened="A.", why_unusual="B.",
                               who_involved="C.", conclusion="D.",
                               suggested_action="Consider enhanced due diligence.")
    assert case.status == "pending_human_review"


def test_record_human_decision_ignores_the_suggestion_entirely():
    """The recorded note must be the OFFICER's words. The suggestion is not
    read by record_human_decision at all — asserted, not assumed."""
    world = seed_world()
    case = investigate("TX-84721", world, use_ai_narrative=False)
    case.narrative = Narrative(source="ai", what_happened="A.", why_unusual="B.",
                               who_involved="C.", conclusion="D.",
                               suggested_action="Close the case, no action needed.")

    case = record_human_decision(case, "officer", "edd", "My own reasoning.", role="officer")

    human_entries = [a for a in case.audit if a.actor == "human"]
    assert human_entries, "the decision must be recorded"
    latest = human_entries[-1]
    assert latest.details["decision"] == "edd", "the officer's decision, not the AI's suggestion"
    assert latest.details["note"] == "My own reasoning."
    assert "Close the case" not in latest.action, "the AI suggestion leaked into the decision record"


def test_officer_may_adopt_the_suggestion_but_it_is_recorded_as_theirs():
    """If an officer genuinely agrees and types it themselves, that's their
    decision — and the record shows it as such, attributed to the human."""
    world = seed_world()
    case = investigate("TX-84721", world, use_ai_narrative=False)
    case = record_human_decision(case, "officer", "edd",
                                 "Agree with the AI suggestion: EDD given the amount deviation.",
                                 role="officer")
    latest = [a for a in case.audit if a.actor == "human"][-1]
    assert latest.actor == "human"
    assert latest.details["role"] == "officer"
    assert case.status == "in_review"


# ── it must be auditable ─────────────────────────────────────────────────

def test_suggestion_is_audit_logged_and_marked_as_a_suggestion(monkeypatch):
    """The point of logging it is to be able to compare, later, what the AI
    advised against what the human actually did."""
    import json as _json
    monkeypatch.setattr(llm, "_call_ollama", lambda *a, **k: _json.dumps({
        "what_happened": "A.", "why_unusual": "B.", "who_involved": "C.", "conclusion": "D.",
        "suggested_action": "Consider enhanced due diligence.",
    }))
    case = investigate("TX-84721", seed_world(), use_ai_narrative=True)
    entry = next((a for a in case.audit if "AI SUGGESTED" in a.action), None)
    assert entry is not None, "the suggestion was not audit-logged"
    assert "not a decision" in entry.action
    assert entry.actor == "system", "a suggestion is not a human action"
    assert entry.details["suggested_action"] == "Consider enhanced due diligence."


def test_no_suggestion_means_no_audit_entry():
    case = investigate("TX-84721", seed_world(), use_ai_narrative=False)
    assert not any("AI SUGGESTED" in a.action for a in case.audit)


def test_suggestion_survives_persistence(tmp_path, monkeypatch):
    import json as _json
    from aci import db
    monkeypatch.setattr(llm, "_call_ollama", lambda *a, **k: _json.dumps({
        "what_happened": "A.", "why_unusual": "B.", "who_involved": "C.", "conclusion": "D.",
        "suggested_action": "Consider enhanced due diligence.",
    }))
    db_path = tmp_path / "aci.db"
    db.init_db(db_path)
    case = investigate("TX-84721", seed_world(), use_ai_narrative=True)
    db.save_case(case, db_path)
    assert db.get_case(case.case_id, db_path).narrative.suggested_action == "Consider enhanced due diligence."


# ── against the real model ───────────────────────────────────────────────

@requires_model
def test_real_model_produces_a_suggestion_that_does_not_claim_to_decide():
    case = investigate("TX-84721", seed_world(), use_ai_narrative=True)
    if case.narrative.source != "ai":
        pytest.skip("model fell back to template on this run")
    s = case.narrative.suggested_action
    assert s, "no suggestion produced"
    lowered = s.lower()
    # It may RECOMMEND closing; it must not assert the case IS closed/cleared.
    for claim in ["case is closed", "case has been closed", "i have closed",
                  "case is cleared", "has been reported", "i have filed"]:
        assert claim not in lowered, f"suggestion claims an action was taken: {s!r}"


@requires_model
def test_real_model_suggestion_does_not_move_the_case_state():
    case = investigate("TX-84721", seed_world(), use_ai_narrative=True)
    assert case.status == "pending_human_review"
    assert case.priority == Severity.HIGH
