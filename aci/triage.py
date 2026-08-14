"""
Alert triage — deciding which case an officer sees first.

Deliberately NOT under aci/agents/: an agent analyses one case and returns an
AgentResult. This ranks a queue of already-analysed cases and returns an
ordering. Filing it as an agent would misrepresent both.

Deterministic and pure: `rank()` takes a list of case summary dicts (exactly
what aci/db.py list_cases() returns) plus an optional clock, and returns them
scored and ordered. No database access, no I/O, no LLM — so it's testable in
isolation and produces identical output for identical input, which is what
lets the queue order be defended rather than just displayed.

Every case carries the REASONS behind its score, not just the number. An
officer who can't see why a case is third cannot sensibly disagree with it,
and a queue you can't argue with is one people quietly stop trusting.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aci import config
from aci.models import SEVERITY_SCORE, Severity

# Terminal states never appear in a work queue — nothing is left to do.
CLOSED_STATUSES = {"closed"}


def _parse(ts: str | datetime | None) -> datetime | None:
    if ts is None:
        return None
    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(ts))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def score_case(case: dict, now: datetime | None = None) -> dict:
    """Score one case. Returns {score, reasons[]} where each reason is
    {code, label, points} — the label is what the UI shows as a chip."""
    now = now or datetime.now(timezone.utc)
    w = config.TRIAGE_WEIGHTS
    reasons: list[dict] = []
    score = 0.0

    sanctions = (case.get("sanctions_status") or "clear").lower()
    if sanctions == "hit":
        score += w["sanctions_hit"]
        reasons.append({"code": "sanctions_hit", "label": "Sanctions match", "points": w["sanctions_hit"]})
    elif sanctions == "possible":
        score += w["sanctions_possible"]
        reasons.append({"code": "sanctions_possible", "label": "Possible sanctions match", "points": w["sanctions_possible"]})

    band = (case.get("priority") or "none").lower()
    band_points = round(w["risk_band"] * SEVERITY_SCORE.get(Severity(band) if band in Severity._value2member_map_ else Severity.NONE, 0.0), 2)
    if band_points:
        score += band_points
        reasons.append({"code": "risk_band", "label": f"{band.upper()} risk", "points": band_points})

    # SLA only means anything for a case actually sitting with the senior
    # reviewer (escalation_level 1). A resolved escalation (level 2) has no
    # clock left to breach.
    if case.get("escalation_level") == 1:
        due = _parse(case.get("sla_due_at"))
        if due:
            hours_left = (due - now).total_seconds() / 3600.0
            if hours_left < 0:
                score += w["sla_breached"]
                reasons.append({"code": "sla_breached",
                               "label": f"SLA breached {_humanise(-hours_left)} ago", "points": w["sla_breached"]})
            elif hours_left <= config.TRIAGE_SLA_IMMINENT_HOURS:
                score += w["sla_imminent"]
                reasons.append({"code": "sla_imminent",
                               "label": f"SLA due in {_humanise(hours_left)}", "points": w["sla_imminent"]})

    created = _parse(case.get("created_at"))
    if created:
        age_days = max(0.0, (now - created).total_seconds() / 86400.0)
        capped = min(age_days, config.TRIAGE_AGE_CAP_DAYS)
        age_points = round(w["age_per_day"] * capped, 2)
        if age_points >= 1.0:  # below a point it's noise, not a reason worth showing
            score += age_points
            reasons.append({"code": "age", "label": f"Open {_humanise(age_days * 24)}", "points": age_points})

    return {"score": round(score, 2), "reasons": reasons}


def _humanise(hours: float) -> str:
    if hours < 1:
        return f"{int(hours * 60)}m"
    if hours < 48:
        return f"{int(hours)}h"
    return f"{int(hours / 24)}d"


def rank(cases: list[dict], now: datetime | None = None, include_closed: bool = False) -> list[dict]:
    """Rank a queue. Closed cases are excluded by default — a work queue is
    for work outstanding.

    The sort is (-score, created_at, case_id): the case_id tiebreak is what
    makes the order STABLE rather than merely correct. Two cases with an
    identical score and timestamp would otherwise swap places between calls
    depending on input order, and a queue that reshuffles under a user's
    cursor is its own kind of bug.
    """
    now = now or datetime.now(timezone.utc)
    ranked = []
    for case in cases:
        if not include_closed and (case.get("status") or "").lower() in CLOSED_STATUSES:
            continue
        scored = score_case(case, now)
        ranked.append({**case, "triage_score": scored["score"], "triage_reasons": scored["reasons"]})

    ranked.sort(key=lambda c: (-c["triage_score"], str(_parse(c.get("created_at")) or ""), c.get("case_id", "")))
    for i, c in enumerate(ranked, start=1):
        c["queue_position"] = i
    return ranked


def explain() -> dict:
    """The ranking model itself, for GET /api/queue — so the UI can show what
    drives the order without hardcoding a second copy of these numbers."""
    return {
        "weights": config.TRIAGE_WEIGHTS,
        "age_cap_days": config.TRIAGE_AGE_CAP_DAYS,
        "sla_imminent_hours": config.TRIAGE_SLA_IMMINENT_HOURS,
        "notes": [
            "Additive priority score — absolute value is meaningless, only the ordering and the ratios between factors matter.",
            "A confirmed sanctions match outranks everything else by construction: it is a legal trigger, not an analytical judgement.",
            "Case age accrues but is capped, so nothing rots at the bottom of the queue and age alone never outranks a real signal.",
            "Closed cases are excluded — this is a work queue, not a case history.",
        ],
    }
