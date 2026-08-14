"""
Deterministic flagging rules (§ same principle as aci/config.py thresholds):
every flag on a live transaction traces to a named, documented, numeric
threshold here — never an LLM judgment call. This mirrors the "never
fabricate, always explainable" discipline of the compliance module.
"""
from __future__ import annotations

from datetime import timedelta

from aci.cybercrime.models import LiveTransaction

# Known mule accounts (synthetic demo blacklist — same "clearly synthetic,
# clearly labelled" posture as every other seed dataset in this project).
MULE_ACCOUNT_BLACKLIST = {
    "AC-MULE-2291", "AC-MULE-5567", "AC-MULE-8834", "AC-MULE-1002", "AC-MULE-7719",
}

# Cities flagged as elevated cybercrime clusters in public awareness material
# (synthetic risk tagging for this demo, not a claim about any real person or
# institution located there).
HIGH_RISK_LOCATIONS = {"Jamtara", "Deoghar", "Bharatpur", "Nuh", "Alwar"}

VELOCITY_WINDOW = timedelta(seconds=300)
VELOCITY_THRESHOLD = 3          # >= this many transfers from one source within the window -> flag
LAYERING_HOP_THRESHOLD = 2      # hop_index >= this (already passed >=2 mule hops) -> flag
HIGH_VALUE_THRESHOLD = 500_000  # INR, single transfer


def evaluate(txn: LiveTransaction, recent_from_source: list[LiveTransaction]) -> tuple[bool, list[str], int]:
    """`recent_from_source` = other transactions from the same source_account
    within VELOCITY_WINDOW, supplied by the caller (aci/cybercrime/store.py
    tracks this) — this function itself stays a pure, testable rule set."""
    reasons: list[str] = []
    score = 0

    if txn.destination_account in MULE_ACCOUNT_BLACKLIST:
        reasons.append(f"Destination {txn.destination_account} is a known mule account.")
        score += 40

    if txn.hop_index >= LAYERING_HOP_THRESHOLD:
        reasons.append(f"Transaction is hop #{txn.hop_index + 1} in a layering chain (>= {LAYERING_HOP_THRESHOLD} mule hops).")
        score += 30

    velocity = len(recent_from_source) + 1  # +1 for this transaction itself
    if velocity >= VELOCITY_THRESHOLD:
        reasons.append(f"{velocity} transfers from {txn.source_account} within {int(VELOCITY_WINDOW.total_seconds())}s (velocity threshold {VELOCITY_THRESHOLD}).")
        score += 25

    if txn.city in HIGH_RISK_LOCATIONS:
        reasons.append(f"Cash-out location '{txn.city}' is a flagged high-risk cluster.")
        score += 20

    if txn.amount >= HIGH_VALUE_THRESHOLD:
        reasons.append(f"Amount ₹{txn.amount:,} is at/above the ₹{HIGH_VALUE_THRESHOLD:,} single-transfer review threshold.")
        score += 15

    score = min(score, 100)
    return (len(reasons) > 0, reasons, score)
