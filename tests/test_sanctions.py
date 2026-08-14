"""
Sanctions / watchlist screening tests.

Screening is the one place where a false negative is a legal problem and a
false positive is an operational one, so both directions are tested — the
deliberate near-miss (TX-66151) matters as much as the deliberate hit
(TX-66150).
"""
from __future__ import annotations

import pytest

from aci import config
from aci.agents import sanctions_agent
from aci.agents.sanctions_agent import match_score, screen_name
from aci.data.synthetic import seed_world
from aci.models import Severity
from aci.orchestrator import investigate


# ── matching primitives ──────────────────────────────────────────────────

def test_exact_match_scores_one():
    assert match_score("Zarnex Petrochemical Trading FZCO", "Zarnex Petrochemical Trading FZCO") == 1.0


def test_matching_is_word_order_independent():
    """'Menon Rajiv' and 'Rajiv Menon' are the same person; a screening system
    that misses this misses a large share of real matches."""
    assert match_score("Dariusz Wolanski", "Wolanski Dariusz") == 1.0


def test_diacritics_are_folded():
    assert match_score("Dariusz Wolanski", "Dariusz Wolański") == 1.0


def test_corporate_suffixes_do_not_inflate_similarity():
    """Two unrelated companies that share only 'Trading FZCO' must not look
    similar — otherwise every free-zone company matches every other one."""
    assert match_score("Alpha Trading FZCO", "Beta Trading FZCO") < config.SANCTIONS_MATCH_POSSIBLE


def test_all_suffix_name_does_not_match_everything():
    """Pathological input: a name made entirely of ignored tokens must not
    normalise to an empty string and then match anything at 1.0."""
    assert match_score("Holdings Ltd", "Zarnex Petrochemical Trading FZCO") < config.SANCTIONS_MATCH_POSSIBLE


def test_empty_and_whitespace_names_score_zero():
    assert match_score("", "Zarnex Petrochemical Trading FZCO") == 0.0
    assert match_score("   ", "Zarnex Petrochemical Trading FZCO") == 0.0


def test_unrelated_name_is_not_reported_at_all():
    assert screen_name("Gulf Consulting Advisory FZE") is None


def test_confirmed_and_possible_bands_are_distinct():
    """The thresholds must actually separate 'stop' from 'look' — a single
    threshold would collapse the distinction screening exists to make."""
    confirmed = screen_name("Zarnex Petrochemicals Trading FZCO")   # plural variant, ~0.98
    assert confirmed is not None and confirmed["confirmed"] is True

    possible = screen_name("Dariusz Wolanek")                        # similar surname, ~0.90
    assert possible is not None and possible["confirmed"] is False
    assert config.SANCTIONS_MATCH_POSSIBLE <= possible["score"] < config.SANCTIONS_MATCH_CONFIRMED


def test_alias_matching_works():
    """Screening only primary names misses trade names and transliterations."""
    hit = screen_name("Zarnex Petrochem FZCO")
    assert hit is not None and hit["confirmed"] is True


# ── agent behaviour ──────────────────────────────────────────────────────

def test_hit_scenario_produces_a_confirmed_finding():
    world = seed_world()
    txn = world.transactions["TX-66150"]
    result = sanctions_agent.run("CASE-T", txn, world)
    assert result.severity == Severity.HIGH
    assert [f.type for f in result.findings] == ["sanctions_hit"]
    assert result.extra["confirmed_hit"] is True


def test_near_miss_scenario_produces_no_finding():
    """The control case. Same customer, same corridor, same amount band — the
    ONLY difference is the beneficiary name, and it must come back clean."""
    world = seed_world()
    txn = world.transactions["TX-66151"]
    result = sanctions_agent.run("CASE-T", txn, world)
    assert result.findings == []
    assert result.severity == Severity.NONE
    assert result.extra["confirmed_hit"] is False
    assert result.extra["possible_match"] is False


def test_clean_screening_still_records_what_was_screened():
    """A clean result must positively assert screening happened — otherwise
    'was this case ever screened?' is unanswerable from the record."""
    world = seed_world()
    result = sanctions_agent.run("CASE-T", world.transactions["TX-66151"], world)
    assert result.extra["subject_count"] >= 1
    assert result.extra["screened"] and all("name" in s for s in result.extra["screened"])
    assert result.extra["lists_screened"]


def test_related_parties_are_screened_not_just_the_beneficiary():
    """Layered ownership is exactly what screening must see through, so
    directors/UBOs surfaced by entity_agent have to be screened too."""
    from aci.agents import entity_agent
    world = seed_world()
    txn = world.transactions["TX-84721"]
    e = entity_agent.run("CASE-84721", txn, world)
    result = sanctions_agent.run("CASE-84721", txn, world, entity_result=e)
    roles = {s["role"] for s in result.extra["screened"]}
    assert "beneficiary" in roles
    assert len(result.extra["screened"]) > 1, "related parties were not screened"


def test_agent_never_asserts_wrongdoing_or_takes_action():
    world = seed_world()
    result = sanctions_agent.run("CASE-T", world.transactions["TX-66150"], world)
    text = " ".join(f.description for f in result.findings).lower()
    assert "guilty" not in text and "criminal" not in text
    # It recommends adjudication; it does not claim to have done anything.
    assert any("confirm or clear" in a.lower() for a in result.recommended_actions)


def test_findings_are_reproducible_across_runs():
    world = seed_world()
    a = sanctions_agent.run("CASE-66150", world.transactions["TX-66150"], world)
    b = sanctions_agent.run("CASE-66150", world.transactions["TX-66150"], world)
    assert [f.id for f in a.findings] == [f.id for f in b.findings]
    assert [f.id for f in a.findings] == ["F-CASE-66150-SAN-001"]


# ── integration: the risk floor ──────────────────────────────────────────

def test_confirmed_hit_forces_high_band_without_altering_the_score():
    """The floor must raise the BAND while leaving the weighted score visible
    and unchanged — hiding the arithmetic would defeat the explainability the
    rest of the risk engine is built around."""
    world = seed_world()
    case = investigate("TX-66150", world, use_ai_narrative=False)
    assert case.priority == Severity.HIGH
    assert case.sanctions_status == "hit"
    assert case.risk.sanctions_floor_applied is not None
    # The rows alone would not have reached HIGH — that's the point of a floor.
    assert case.risk.score < 0.70


def test_near_miss_case_is_not_floored():
    world = seed_world()
    case = investigate("TX-66151", world, use_ai_narrative=False)
    assert case.sanctions_status == "clear"
    assert case.risk.sanctions_floor_applied is None


def test_the_pair_differs_only_in_screening_outcome():
    """Both demo transactions are constructed to score identically, so any
    band difference between them is attributable to screening alone."""
    world = seed_world()
    hit = investigate("TX-66150", world, use_ai_narrative=False)
    clean = investigate("TX-66151", world, use_ai_narrative=False)
    assert hit.risk.score == clean.risk.score
    assert hit.priority != clean.priority


def test_sanctions_result_is_in_agent_results_and_audit():
    world = seed_world()
    case = investigate("TX-66150", world, use_ai_narrative=False)
    assert any(r.dimension == "sanctions" for r in case.agent_results)
    assert any("Sanctions screening" in a.action for a in case.audit)


def test_clean_case_is_also_audit_logged():
    world = seed_world()
    case = investigate("TX-66151", world, use_ai_narrative=False)
    assert any("Sanctions screening: no match" in a.action for a in case.audit)


def test_screening_runs_without_ollama(monkeypatch):
    """Screening is deterministic and must be unaffected by the LLM being
    down — the whole point of keeping detection out of the model."""
    monkeypatch.setattr("aci.llm.ollama_status", lambda: {"available": False})
    world = seed_world()
    case = investigate("TX-66150", world, use_ai_narrative=False)
    assert case.priority == Severity.HIGH
    assert case.sanctions_status == "hit"


# ── persistence ──────────────────────────────────────────────────────────

def test_sanctions_status_persists_and_is_queryable(tmp_path):
    from aci import db
    db_path = tmp_path / "aci.db"
    db.init_db(db_path)
    world = seed_world()
    case = investigate("TX-66150", world, use_ai_narrative=False)
    db.save_case(case, db_path)

    reloaded = db.get_case(case.case_id, db_path)
    assert reloaded.sanctions_status == "hit"
    # And queryable from the lightweight list without deserialising the blob.
    row = next(c for c in db.list_cases(db_path) if c["case_id"] == case.case_id)
    assert row["sanctions_status"] == "hit"


def test_legacy_db_without_sanctions_column_migrates(tmp_path):
    """A database created before this feature must upgrade in place, not
    require a wipe (same standard as the escalation migration)."""
    import sqlite3
    from aci import db
    old = tmp_path / "legacy.db"
    conn = sqlite3.connect(str(old))
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

    world = seed_world()
    case = investigate("TX-66150", world, use_ai_narrative=False)
    db.save_case(case, old)  # must not raise
    assert db.get_case(case.case_id, old).sanctions_status == "hit"


# ── API ──────────────────────────────────────────────────────────────────

def test_sanctions_endpoint_returns_screening_detail(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from aci import config as cfg, db

    monkeypatch.setattr(cfg, "DB_PATH", tmp_path / "aci.db")
    from aci.api.app import app
    db.init_db(cfg.DB_PATH)

    client = TestClient(app)
    created = client.post("/api/investigations", json={"transaction_id": "TX-66150"}).json()
    body = client.get(f"/api/sanctions/{created['case_id']}").json()

    assert body["status"] == "hit"
    assert body["findings"] and body["findings"][0]["type"] == "sanctions_hit"
    assert body["screened"]
    assert body["known_limitations"], "limitations must be surfaced, not just documented in code"
    assert "FABRICATED" in body["disclaimer"].upper()
    assert body["risk_floor_applied"]
