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
}


def _refs_for(dim: str, txn, results: dict[str, AgentResult]) -> list[str]:
    """The specific signal/finding IDs behind a dimension's severity, so every
    row in the risk breakdown traces back to concrete evidence."""
    if dim == "jurisdiction":
        return [f"route:{'→'.join(txn.route)}"] if len(txn.route) >= 2 else []
    r = results.get(dim)
    if not r:
        return []
    return [s.type for s in r.signals] + [f.id for f in r.findings]


def run(case_id: str, txn, results: dict[str, AgentResult]) -> RiskAssessment:
    sev_by_dim = {
        "transaction": results["transaction"].severity,
        "entity": results["entity"].severity,
        "regulatory": results["regulatory"].severity,
        "documentation": results["documentation"].severity,
        "jurisdiction": (Severity.MEDIUM if len(txn.route) >= 3 else
                         Severity.LOW if len(txn.route) == 2 else Severity.NONE),
    }
    rows = []
    for key, weight in config.RISK_WEIGHTS.items():
        sev = sev_by_dim.get(key, Severity.NONE)
        rows.append(RiskRow(key=key, label=_RISK_LABELS[key], weight=weight,
                            severity=sev, contribution=round(weight * SEVERITY_SCORE[sev], 4),
                            source_refs=_refs_for(key, txn, results)))
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
