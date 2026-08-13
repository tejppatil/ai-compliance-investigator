"""
Agent 1 — Transaction Intelligence (§7).

Do NOT ask an LLM to do numerical anomaly detection. This is pure statistics:
median, ratios, velocity, threshold clustering. The LLM (later) only explains.
"""
from __future__ import annotations

import statistics
from datetime import datetime

from aci import config
from aci.data.synthetic import World
from aci.models import AgentResult, Severity, Signal, SEVERITY_SCORE, band_from_score


def _months_between(a: str, b: str) -> int:
    da = datetime.fromisoformat(a[:10])
    db = datetime.fromisoformat(b[:10])
    return max(0, round((db - da).days / 30.44))


def run(case_id: str, txn, world: World) -> AgentResult:
    hist = world.hist(txn.customer_id)
    amounts = [h["amount"] for h in hist]
    med = statistics.median(amounts) if amounts else txn.amount
    ratio = txn.amount / med if med else 1.0
    routes_seen = {h["dest"] for h in hist}
    cp_age = _months_between(txn.beneficiary_registered, txn.timestamp)

    signals: list[Signal] = []

    if ratio >= config.AMOUNT_RATIO_HIGH:
        signals.append(Signal(type="amount_anomaly", severity=Severity.HIGH, metric=f"{ratio:.2f}x",
                              explanation=f"{ratio:.1f}x the customer's historical median (INR {med:,.0f})."))
    elif ratio >= config.AMOUNT_RATIO_MEDIUM:
        signals.append(Signal(type="amount_anomaly", severity=Severity.MEDIUM, metric=f"{ratio:.2f}x",
                              explanation=f"{ratio:.1f}x the historical median (INR {med:,.0f})."))

    if cp_age <= config.NEW_COUNTERPARTY_MONTHS:
        signals.append(Signal(type="new_counterparty", severity=Severity.MEDIUM, metric=f"{cp_age}mo",
                              explanation=f"Beneficiary onboarded ~{cp_age} month(s) before the transaction; no prior settled history."))

    if txn.destination_country not in routes_seen and txn.destination_country != txn.source_country:
        signals.append(Signal(type="route_change", severity=Severity.MEDIUM, metric="→".join(txn.route),
                              explanation=f"New jurisdictional route for this customer ({' → '.join(txn.route)})."))

    near = [h for h in hist if config.REPORTING_THRESHOLD * config.STRUCTURING_BAND <= h["amount"] < config.REPORTING_THRESHOLD]
    if len(near) >= 3:
        signals.append(Signal(type="structuring", severity=Severity.HIGH, metric=f"{len(near)} near-threshold",
                              explanation=f"{len(near)} recent transfers sit just below the INR {config.REPORTING_THRESHOLD:,} reporting threshold."))

    # velocity (compare calendar dates to avoid tz-aware vs naive mismatch)
    if hist:
        t = datetime.fromisoformat(txn.timestamp).date()
        last30 = sum(1 for h in hist if 0 <= (t - datetime.fromisoformat(h["date"]).date()).days <= 30) + 1
        baseline = max(1, round(len(hist) / 7))
        if last30 >= baseline * config.VELOCITY_MULTIPLIER and len(hist) >= 4:
            # A burst that is merely "elevated" is MEDIUM; a burst several
            # multiples above baseline, combined with multi-hop routing
            # (funds moving across 3+ jurisdictions), is the rapid-movement /
            # layering pattern and warrants HIGH on its own rather than being
            # too weak to ever cross the risk-band threshold alongside it.
            rapid_layering = last30 >= baseline * config.VELOCITY_MULTIPLIER * 1.5 and len(txn.route) >= 3
            severity = Severity.HIGH if rapid_layering else Severity.MEDIUM
            signal_type = "rapid_movement" if rapid_layering else "velocity"
            explanation = (f"Trailing-30-day activity ({last30}) is elevated vs baseline cadence ({baseline})"
                           + (f", combined with multi-hop routing ({' → '.join(txn.route)})." if rapid_layering else "."))
            signals.append(Signal(type=signal_type, severity=severity, metric=f"{last30}/30d", explanation=explanation))

    worst = max((SEVERITY_SCORE[s.severity] for s in signals), default=0.0)
    return AgentResult(
        agent="transaction_intelligence", case_id=case_id, dimension="transaction",
        severity=band_from_score(worst), signals=signals,
        unknowns=[] if signals else ["No behavioural deviation detected against baseline."],
        recommended_actions=["Review recent transaction history against stated purpose."] if signals else [],
        extra={"median": med, "ratio": ratio, "counterparty_age_months": cp_age, "routes_seen": sorted(routes_seen)},
    )
