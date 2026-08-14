"""
Agent — Sanctions / Watchlist Screening.

Screens every counterparty and every person/entity the Entity Intelligence
agent surfaced (directors, beneficial owners) against a bundled FABRICATED
watchlist (aci/data/synthetic_watchlist.py). No real sanctions list is used.

Design notes worth being explicit about, because screening is the step most
easily made to look better than it is:

1. **Deterministic, no LLM.** Matching is string similarity with documented
   thresholds from aci/config.py. Identical inputs always give identical
   scores and identical finding IDs, so the audit trail is reproducible.

2. **Two outcomes, not one.** A near-exact match is a `sanctions_hit`; a
   plausible-but-uncertain one is a `sanctions_possible_match` for a human to
   confirm or clear. Collapsing these loses the distinction between "stop"
   and "look" — the distinction screening exists to make.

3. **Suffix-stripped token-sort matching.** Real screening has to survive
   word-order variance ("Menon Rajiv" vs "Rajiv Menon") and meaningless
   corporate suffixes ("Ltd", "FZCO") that make unrelated names look similar.
   Tokens are normalised (diacritics folded, punctuation dropped, suffixes
   removed per config.SANCTIONS_IGNORED_TOKENS), sorted, then compared with
   stdlib difflib. That's deliberately a lightweight approach — see
   `KNOWN_LIMITATIONS` below for what it does NOT do, because claiming
   production-grade name screening here would be dishonest.

4. **A hit is a finding, not a verdict.** The agent never blocks, freezes, or
   files anything; it reports, and the risk engine applies a documented floor
   (aci/agents/risk_agent.py). A human still decides (§13).
"""
from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

from aci import config
from aci.data.synthetic import World
from aci.data.synthetic_watchlist import all_entries
from aci.models import AgentResult, Finding, Severity, SEVERITY_SCORE, band_from_score

# Stated plainly so nobody reads this as production screening. A real
# programme would also need: phonetic/soft matching (Soundex/Metaphone,
# Arabic/Cyrillic transliteration tables), date-of-birth and nationality
# corroboration to cut false positives on common names, list versioning with
# an auditable refresh cadence, and secondary-sanctions/ownership-percentage
# rules (e.g. the 50%-owned-by-a-designated-party principle).
KNOWN_LIMITATIONS = [
    "Latin-script similarity only — no phonetic or cross-script transliteration matching.",
    "No date-of-birth / nationality corroboration, so common personal names over-match by design.",
    "Bundled static list — no versioning or refresh cadence (a licensed feed would supply both).",
    "No ownership-percentage (e.g. 50%-owned-by-designated-party) derivation.",
]

_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)


def _normalise(name: str) -> list[str]:
    """Fold diacritics, drop punctuation, lowercase, and remove non-identifying
    corporate suffixes — 'Dariusz Wolański' and 'Dariusz Wolanski' must reach
    the same tokens, and 'Ltd'/'FZCO' must not inflate similarity."""
    folded = unicodedata.normalize("NFKD", name)
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    folded = _PUNCT.sub(" ", folded).lower()
    tokens = [t for t in folded.split() if t and t not in config.SANCTIONS_IGNORED_TOKENS]
    # If a name is ENTIRELY suffixes (pathological, e.g. "Holdings Ltd"), keep
    # the raw tokens rather than comparing two empty strings — which would
    # otherwise score 1.0 and match everything.
    return tokens or [t for t in folded.split() if t]


def match_score(a: str, b: str) -> float:
    """Token-sort similarity in [0.0, 1.0]. Sorting the tokens before
    comparison is what makes word order irrelevant."""
    ta, tb = _normalise(a), _normalise(b)
    if not ta or not tb:
        return 0.0
    if ta == tb:
        return 1.0
    return SequenceMatcher(None, " ".join(sorted(ta)), " ".join(sorted(tb))).ratio()


def screen_name(name: str) -> dict | None:
    """Best match for one name across every watchlist entry and alias.
    Returns None below config.SANCTIONS_MATCH_POSSIBLE."""
    best: dict | None = None
    for entry in all_entries():
        for candidate in [entry["name"], *entry.get("aliases", [])]:
            score = match_score(name, candidate)
            if best is None or score > best["score"]:
                best = {"score": score, "matched_name": candidate, "entry": entry}
    if not best or best["score"] < config.SANCTIONS_MATCH_POSSIBLE:
        return None
    best["confirmed"] = best["score"] >= config.SANCTIONS_MATCH_CONFIRMED
    return best


def _subjects(txn, world: World, entity_result: AgentResult | None) -> list[tuple[str, str]]:
    """(name, role) pairs to screen: the beneficiary, plus every entity the
    Entity Intelligence agent named as a director / beneficial owner. Screening
    only the direct counterparty would miss exactly the layered-ownership case
    that agent exists to find."""
    subjects: list[tuple[str, str]] = []
    seen: set[str] = set()

    def add(entity_id: str, role: str) -> None:
        ent = world.entity(entity_id)
        if ent and ent.name not in seen:
            seen.add(ent.name)
            subjects.append((ent.name, role))

    add(txn.beneficiary_id, "beneficiary")
    if entity_result:
        for finding in entity_result.findings:
            for node_id in finding.nodes:
                if node_id != txn.beneficiary_id:
                    add(node_id, "related party (director / beneficial owner)")
    return subjects


def run(case_id: str, txn, world: World, entity_result: AgentResult | None = None) -> AgentResult:
    """`entity_result` lets the orchestrator pass Entity Intelligence's output
    so related parties get screened too — the orchestrator always supplies it;
    it's optional only so the agent stays independently testable."""
    findings: list[Finding] = []
    fid = 0

    def _next_fid() -> str:
        nonlocal fid
        fid += 1
        return f"F-{case_id}-SAN-{fid:03d}"

    subjects = _subjects(txn, world, entity_result)
    screened: list[dict] = []

    for name, role in subjects:
        hit = screen_name(name)
        screened.append({"name": name, "role": role, "hit": bool(hit),
                        "score": round(hit["score"], 3) if hit else 0.0})
        if not hit:
            continue
        entry = hit["entry"]
        confirmed = hit["confirmed"]
        findings.append(Finding(
            id=_next_fid(),
            type="sanctions_hit" if confirmed else "sanctions_possible_match",
            severity=Severity.HIGH if confirmed else Severity.MEDIUM,
            description=(
                f"{'MATCH' if confirmed else 'POSSIBLE MATCH'}: {role} \"{name}\" matches "
                f"\"{hit['matched_name']}\" ({entry['entry_id']}) on the {entry['list']} "
                f"at {hit['score']:.0%} similarity. Designated {entry['designated_on']} "
                f"under {entry['programme']}."
                + ("" if confirmed else " Below the confirmed-match threshold — requires human confirmation before any action.")
            ),
            confidence=round(hit["score"], 2),
            nodes=[txn.beneficiary_id],
        ))

    confirmed_hits = [f for f in findings if f.type == "sanctions_hit"]
    worst = max((SEVERITY_SCORE[f.severity] for f in findings), default=0.0)

    unknowns, actions = [], []
    if confirmed_hits:
        unknowns.append("Screening matched on name similarity only — identity has NOT been corroborated "
                       "against date of birth, registration number, or nationality.")
        actions += ["Confirm or clear the watchlist match against the underlying list record before acting.",
                   "Do not process further until a compliance officer has adjudicated the match."]
    elif findings:
        unknowns.append("Possible watchlist match below the confirmed threshold — a human must confirm or clear it.")
        actions.append("Manually review the possible watchlist match and record the adjudication.")

    return AgentResult(
        agent="sanctions_screening", case_id=case_id, dimension="sanctions",
        severity=band_from_score(worst), findings=findings,
        unknowns=unknowns, recommended_actions=actions,
        extra={
            "screened": screened,
            "subject_count": len(subjects),
            "confirmed_hit": bool(confirmed_hits),
            "possible_match": bool(findings) and not confirmed_hits,
            "lists_screened": sorted({e["list"] for e in all_entries()}),
            "thresholds": {"confirmed": config.SANCTIONS_MATCH_CONFIRMED,
                          "possible": config.SANCTIONS_MATCH_POSSIBLE},
            "disclaimer": "Screened against a FABRICATED watchlist bundled with this prototype. "
                          "No real sanctions list is used. Not a real screening result.",
            "known_limitations": KNOWN_LIMITATIONS,
        },
    )
