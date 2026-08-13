"""
Agent 4 — Risk Engine (§10, §18).

Explainable weighted aggregation. Not a black-box number: every dimension's
severity is derived from an agent's finding, weighted by a documented,
configurable weight, and the contributions are shown. Confidence is computed
SEPARATELY from risk — confidence is evidence quality, not a fraud probability.
"""
from __future__ import annotations

from aci import config
from aci.models import (AgentResult, RiskAssessment, RiskRow, Severity,
                        SEVERITY_SCORE, band_from_score)

_RISK_LABELS = {
    "transaction": "Transaction anomaly",
    "entity": "Entity anomaly",
    "regulatory": "Regulatory concern",
    "documentation": "Documentation anomaly",
    "jurisdiction": "Jurisdictional complexity",
    "customer_risk": "Customer risk rating",
}

# One sentence per dimension — surfaced via GET /api/risk-methodology so the
# frontend's Risk-Based Approach page renders real backend text, not a
# hardcoded copy that could drift from what the engine actually does.
_RISK_DESCRIPTIONS = {
    "transaction": "Statistical behaviour vs. the customer's own transaction history — amount ratio, velocity, structuring, layering.",
    "entity": "Ownership and relationship structure — shared directors, beneficial-owner chains, unverified UBOs.",
    "regulatory": "Applicable controls retrieved from the regulatory knowledge base for this transaction's jurisdictions and attributes.",
    "documentation": "Consistency between the invoice/document and the transaction it supports — generic narratives, amount mismatches, missing documents.",
    "jurisdiction": "Geographic complexity of the payment route — number of jurisdictions the funds pass through.",
    "customer_risk": "The customer's own persistent risk rating (FATF R.1) — independent of any single transaction's behaviour.",
}


def _refs_for(dim: str, txn, results: dict[str, AgentResult], customer=None) -> list[str]:
    """The specific signal/finding IDs behind a dimension's severity, so every
    row in the risk breakdown traces back to concrete evidence."""
    if dim == "jurisdiction":
        return [f"route:{'→'.join(txn.route)}"] if len(txn.route) >= 2 else []
    if dim == "customer_risk":
        return [f"customer_risk_profile:{customer.risk_profile}"] if customer else []
    r = results.get(dim)
    if not r:
        return []
    return [s.type for s in r.signals] + [f.id for f in r.findings]


def run(case_id: str, txn, results: dict[str, AgentResult], customer=None) -> RiskAssessment:
    """`customer` grounds the customer_risk dimension in the Risk-Based
    Approach (§ FATF R.1) — a persistent customer risk rating, not just this
    transaction's own behaviour. Optional only so existing direct callers
    (e.g. ad-hoc tests) don't break; the orchestrator always passes it."""
    risk_profile = customer.risk_profile if customer else "standard"
    sev_by_dim = {
        "transaction": results["transaction"].severity,
        "entity": results["entity"].severity,
        "regulatory": results["regulatory"].severity,
        "documentation": results["documentation"].severity,
        "jurisdiction": (Severity.MEDIUM if len(txn.route) >= 3 else
                         Severity.LOW if len(txn.route) == 2 else Severity.NONE),
        "customer_risk": config.CUSTOMER_RISK_SEVERITY.get(risk_profile, config.CUSTOMER_RISK_SEVERITY["standard"]),
    }
    rows = []
    for key, weight in config.RISK_WEIGHTS.items():
        sev = sev_by_dim.get(key, Severity.NONE)
        rows.append(RiskRow(key=key, label=_RISK_LABELS[key], weight=weight,
                            severity=sev, contribution=round(weight * SEVERITY_SCORE[sev], 4),
                            source_refs=_refs_for(key, txn, results, customer)))
    score = round(sum(r.contribution for r in rows), 4)

    # confidence = mean of available finding confidences + retrieval/signal presence
    confs = []
    for f in results["entity"].findings:
        confs.append(f.confidence)
    if results["regulatory"].regulatory:
        confs.append(0.90)
    if results["transaction"].signals:
        confs.append(0.86)
    confidence = round(sum(confs) / len(confs), 2) if confs else 0.5

    return RiskAssessment(rows=rows, score=score, band=band_from_score(score), confidence=confidence)
