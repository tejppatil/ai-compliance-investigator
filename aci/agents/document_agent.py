"""
Document Analysis Agent (§17).

Extracts basic structured fields from the transaction's attached document
(amount, narrative) and reconciles them against the transaction itself —
the amount-mismatch check the blueprint calls for, which the earlier
word-count-only `document_check` never performed despite `Document.amount`
already existing in the model.

Document text is analysed as content, never as instruction (§24, §30) — this
agent only reads structured fields off `Document`; nothing here executes
anything found inside a narrative.
"""
from __future__ import annotations

from aci.data.synthetic import World
from aci.models import AgentResult, Finding, Severity, SEVERITY_SCORE, band_from_score

GENERIC_NARRATIVE_WORD_LIMIT = 3
AMOUNT_MISMATCH_THRESHOLD = 0.05   # >5% deviation between invoice and transaction amount
AMOUNT_MISMATCH_HIGH = 0.25        # >25% deviation escalates to HIGH


def run(case_id: str, txn, world: World) -> AgentResult:
    doc = world.doc(txn.transaction_id)
    findings: list[Finding] = []
    fid = 0

    def _next_fid() -> str:
        nonlocal fid
        fid += 1
        return f"F-{case_id}-DOC-{fid:03d}"

    if not doc:
        findings.append(Finding(
            id=_next_fid(), type="missing_documentation", severity=Severity.HIGH,
            description="No supporting documentation attached to the transaction.",
            confidence=0.95))
    else:
        word_count = len(doc.narrative.split())
        if word_count <= GENERIC_NARRATIVE_WORD_LIMIT and txn.amount >= 5_000_000:
            findings.append(Finding(
                id=_next_fid(), type="generic_narrative", severity=Severity.MEDIUM,
                description=(f'Invoice narrative ("{doc.narrative}") is generic relative to '
                            f'an INR {txn.amount:,} value.'),
                confidence=0.70))

        if doc.amount and doc.amount != txn.amount:
            deviation = abs(doc.amount - txn.amount) / max(doc.amount, txn.amount)
            if deviation > AMOUNT_MISMATCH_THRESHOLD:
                severity = Severity.HIGH if deviation > AMOUNT_MISMATCH_HIGH else Severity.MEDIUM
                findings.append(Finding(
                    id=_next_fid(), type="amount_mismatch", severity=severity,
                    description=(f"Invoice amount INR {doc.amount:,} does not match the transaction "
                                f"amount INR {txn.amount:,} ({deviation * 100:.0f}% deviation). "
                                "Flagged for investigation — this alone does not establish fraud."),
                    confidence=0.80))

    worst = max((SEVERITY_SCORE[f.severity] for f in findings), default=0.0)
    return AgentResult(
        agent="document_analysis", case_id=case_id, dimension="documentation",
        severity=band_from_score(worst), findings=findings,
        unknowns=["No documentation available to verify commercial rationale."] if not doc else [],
        recommended_actions=["Request additional supporting documentation and reconcile against the transaction."] if findings else [],
    )
