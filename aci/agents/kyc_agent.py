"""
Agent — KYC Completeness (§8, §17-adjacent).

Checks the customer's own onboarding record for internal consistency and
completeness — NOT a risk-scoring agent. This is a data-quality check: does
the corporate KYC record we already have (Customer + linked Entity +
Relationship rows in aci/data/synthetic.py) actually hold together? A
mismatch here means "our own records are incomplete or inconsistent," which
is a real, separate finding from "this transaction looks unusual" — mixing
the two into the risk score would misrepresent what's actually being
measured, so this agent's severity is NOT one of the aci/config.py
RISK_WEIGHTS dimensions and never enters the risk score (see
aci/orchestrator.py — it runs alongside the other agents but risk_agent.run()
never reads its result).

Deliberately NOT an OCR/biometric pipeline: this system investigates
already-onboarded corporate customers in a B2B cross-border corridor, not
retail signups, so the honest equivalent of "cross-check identity documents"
is "cross-check the corporate records we hold," not face-matching a selfie.
"""
from __future__ import annotations

from datetime import datetime

from aci.data.synthetic import World
from aci.models import AgentResult, Finding, Severity, SEVERITY_SCORE, band_from_score


def _date(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s[:10])
    except ValueError:
        return None


def run(case_id: str, txn, world: World) -> AgentResult:
    customer = world.customer(txn.customer_id)
    entity = world.entity(customer.entity_id) if customer.entity_id else None
    findings: list[Finding] = []
    fid = 0

    def _next_fid() -> str:
        nonlocal fid
        fid += 1
        return f"F-{case_id}-KYC-{fid:03d}"

    if not entity:
        findings.append(Finding(
            id=_next_fid(), type="kyc_missing_ownership", severity=Severity.MEDIUM,
            description=f"Customer {customer.name} has no linked corporate entity record on file.",
            confidence=0.95))
    else:
        if entity.name.strip().lower() != customer.name.strip().lower():
            findings.append(Finding(
                id=_next_fid(), type="kyc_name_mismatch", severity=Severity.LOW,
                description=(f'Customer record name ("{customer.name}") does not exactly match its '
                            f'linked entity name ("{entity.name}") — confirm these describe the same legal person.'),
                confidence=0.60))

        if not entity.registered or not entity.directors:
            missing = []
            if not entity.registered:
                missing.append("registration date")
            if not entity.directors:
                missing.append("director/beneficial-owner record")
            findings.append(Finding(
                id=_next_fid(), type="kyc_missing_ownership", severity=Severity.MEDIUM,
                description=f"Entity record for {entity.name} is missing: {', '.join(missing)}.",
                confidence=0.90))

        reg, onboarded = _date(entity.registered), _date(customer.onboarded)
        if reg and onboarded and reg > onboarded:
            findings.append(Finding(
                id=_next_fid(), type="kyc_date_inconsistency", severity=Severity.MEDIUM,
                description=(f"{entity.name}'s registration date ({entity.registered}) falls AFTER the "
                            f"customer's own onboarding date ({customer.onboarded}) — a data-quality "
                            "inconsistency worth confirming, not evidence of wrongdoing."),
                confidence=0.85))

    worst = max((SEVERITY_SCORE[f.severity] for f in findings), default=0.0)
    complete = not findings
    return AgentResult(
        agent="kyc_completeness", case_id=case_id, dimension="kyc",
        severity=band_from_score(worst), findings=findings,
        unknowns=[] if complete else ["KYC record completeness/consistency issue — confirm with onboarding records."],
        recommended_actions=["Refresh the KYC record for this customer before closing the case."] if findings else [],
        extra={"complete": complete, "note": "Data-quality check on our own onboarding record — not a risk-scoring dimension."},
    )
