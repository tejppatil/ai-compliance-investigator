"""
Alert triage / queue ranking tests.

Ranking is pure and clock-injectable, so every one of these asserts an exact
ordering rather than "roughly sorts" — a queue that's only approximately
right is one an officer can't rely on.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aci import config, triage

NOW = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)


def _case(case_id, *, priority="low", status="pending_human_review", sanctions="clear",
          escalation_level=0, sla_hours=None, age_days=0.0):
    return {
        "case_id": case_id,
        "transaction_id": f"TX-{case_id}",
        "priority": priority,
        "status": status,
        "sanctions_status": sanctions,
        "escalation_level": escalation_level,
        "sla_due_at": (NOW + timedelta(hours=sla_hours)).isoformat() if sla_hours is not None else None,
        "created_at": (NOW - timedelta(days=age_days)).isoformat(),
    }


def _order(cases):
    return [c["case_id"] for c in triage.rank(cases, now=NOW)]


# ── ordering ─────────────────────────────────────────────────────────────

def test_sanctions_hit_outranks_a_high_risk_case():
    """The central claim of the ranking model: a legal trigger beats an
    analytical judgement, even a maximal one."""
    cases = [_case("HIGH", priority="high"), _case("SANC", priority="low", sanctions="hit")]
    assert _order(cases) == ["SANC", "HIGH"]


def test_sanctions_hit_outranks_a_breached_sla():
    cases = [
        _case("SLA", priority="high", escalation_level=1, sla_hours=-30),
        _case("SANC", priority="none", sanctions="hit"),
    ]
    assert _order(cases) == ["SANC", "SLA"]


def test_possible_match_ranks_below_a_confirmed_one():
    cases = [_case("POSS", sanctions="possible"), _case("HIT", sanctions="hit")]
    assert _order(cases) == ["HIT", "POSS"]


def test_risk_band_orders_cases_with_nothing_else_going_on():
    cases = [_case("L", priority="low"), _case("H", priority="high"), _case("M", priority="medium")]
    assert _order(cases) == ["H", "M", "L"]


def test_breached_sla_outranks_imminent_sla():
    cases = [
        _case("IMMINENT", escalation_level=1, sla_hours=2),
        _case("BREACHED", escalation_level=1, sla_hours=-2),
    ]
    assert _order(cases) == ["BREACHED", "IMMINENT"]


def test_age_breaks_a_tie_between_otherwise_identical_cases():
    cases = [_case("NEW", priority="medium", age_days=0), _case("OLD", priority="medium", age_days=5)]
    assert _order(cases) == ["OLD", "NEW"]


def test_age_alone_never_outranks_a_real_signal():
    """The age cap exists so a stale nothing-case can't climb over a fresh
    high-risk one purely by sitting there."""
    cases = [
        _case("ANCIENT", priority="none", age_days=365),
        _case("FRESH_HIGH", priority="high", age_days=0),
    ]
    assert _order(cases) == ["FRESH_HIGH", "ANCIENT"]


# ── SLA scoping ──────────────────────────────────────────────────────────

def test_sla_only_counts_while_awaiting_senior_review():
    """escalation_level 2 means the senior already decided — there is no
    clock left to breach, so a stale timestamp must not keep scoring."""
    resolved = _case("RESOLVED", escalation_level=2, sla_hours=-100)
    scored = triage.score_case(resolved, now=NOW)
    assert not any(r["code"].startswith("sla") for r in scored["reasons"])


def test_sla_is_ignored_for_an_unescalated_case():
    scored = triage.score_case(_case("PLAIN", escalation_level=0, sla_hours=-100), now=NOW)
    assert not any(r["code"].startswith("sla") for r in scored["reasons"])


def test_sla_far_in_the_future_scores_nothing():
    scored = triage.score_case(_case("LATER", escalation_level=1, sla_hours=48), now=NOW)
    assert not any(r["code"].startswith("sla") for r in scored["reasons"])


# ── determinism & stability ──────────────────────────────────────────────

def test_ranking_is_deterministic():
    cases = [_case("A", priority="high"), _case("B", sanctions="hit"), _case("C", priority="medium")]
    assert _order(cases) == _order(cases) == _order(cases)


def test_ranking_is_stable_regardless_of_input_order():
    """Identical scores must not reshuffle depending on how the DB happened
    to return the rows — a queue that reorders under the cursor is a bug."""
    a = _case("AAA", priority="medium", age_days=1)
    b = _case("BBB", priority="medium", age_days=1)
    c = _case("CCC", priority="medium", age_days=1)
    assert _order([a, b, c]) == _order([c, b, a]) == _order([b, a, c])


def test_score_is_the_sum_of_its_stated_reasons():
    """The chips shown to the officer must actually account for the number —
    an unexplained residual would make the explanation a decoration."""
    scored = triage.score_case(
        _case("X", priority="high", sanctions="hit", escalation_level=1, sla_hours=-1, age_days=3), now=NOW)
    assert round(sum(r["points"] for r in scored["reasons"]), 2) == scored["score"]


# ── queue semantics ──────────────────────────────────────────────────────

def test_closed_cases_are_excluded_by_default():
    cases = [_case("OPEN"), _case("DONE", status="closed", priority="high", sanctions="hit")]
    assert _order(cases) == ["OPEN"]


def test_closed_cases_can_be_included_explicitly():
    cases = [_case("OPEN"), _case("DONE", status="closed", priority="high", sanctions="hit")]
    ids = [c["case_id"] for c in triage.rank(cases, now=NOW, include_closed=True)]
    assert set(ids) == {"OPEN", "DONE"}


def test_queue_positions_are_assigned_from_one():
    ranked = triage.rank([_case("A", priority="high"), _case("B")], now=NOW)
    assert [c["queue_position"] for c in ranked] == [1, 2]


def test_empty_queue_is_handled():
    assert triage.rank([], now=NOW) == []


def test_malformed_timestamps_do_not_crash_the_queue():
    """Real queues meet bad rows; one unparseable date must not take the
    whole list down."""
    bad = {"case_id": "BAD", "priority": "high", "status": "pending_human_review",
           "sanctions_status": "clear", "escalation_level": 1,
           "sla_due_at": "not-a-date", "created_at": None}
    ranked = triage.rank([bad, _case("GOOD")], now=NOW)
    assert {c["case_id"] for c in ranked} == {"BAD", "GOOD"}


def test_unknown_priority_value_is_treated_as_none_not_an_error():
    scored = triage.score_case({"case_id": "W", "priority": "catastrophic", "status": "open",
                                "created_at": NOW.isoformat()}, now=NOW)
    assert scored["score"] >= 0


# ── model transparency ───────────────────────────────────────────────────

def test_explain_exposes_the_real_weights():
    model = triage.explain()
    assert model["weights"] == config.TRIAGE_WEIGHTS
    assert model["age_cap_days"] == config.TRIAGE_AGE_CAP_DAYS


# ── API ──────────────────────────────────────────────────────────────────

def test_queue_endpoint_returns_ranked_cases_and_the_model(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from aci import config as cfg, db
    from aci.data.synthetic import seed_world
    from aci.orchestrator import investigate

    monkeypatch.setattr(cfg, "DB_PATH", tmp_path / "aci.db")
    from aci.api.app import app
    db.init_db(cfg.DB_PATH)

    world = seed_world()
    for tid in ("TX-77310", "TX-66150"):  # a quiet case and the sanctions hit
        db.save_case(investigate(tid, world, use_ai_narrative=False), cfg.DB_PATH)

    body = TestClient(app).get("/api/queue").json()
    assert body["model"]["weights"] == config.TRIAGE_WEIGHTS
    assert body["cases"][0]["transaction_id"] == "TX-66150", "sanctions hit should lead the queue"
    assert any(r["code"] == "sanctions_hit" for r in body["cases"][0]["triage_reasons"])
    assert body["cases"][0]["queue_position"] == 1
