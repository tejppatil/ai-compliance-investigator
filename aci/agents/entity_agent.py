"""
Agent 2 — Entity Intelligence (§8).

Understands who is involved via graph traversal. Crucially: a detected
relationship is NOT evidence of wrongdoing — the agent says only
"relationship detected, additional due diligence recommended".
"""
from __future__ import annotations

from aci.data.synthetic import World
from aci.models import AgentResult, Finding, Severity, SEVERITY_SCORE, band_from_score


def _sender_entity(world: World, txn) -> str | None:
    """Resolve the sender-side entity via the customer's explicit entity_id
    link. Falls back to a name match only for legacy records that predate the
    link, so demo/test data keeps working without silently misresolving bulk-
    generated records whose names never coincide (§ evaluation)."""
    cust = world.customer(txn.customer_id)
    if cust.entity_id and world.entity(cust.entity_id):
        return cust.entity_id
    for eid, e in world.entities.items():
        if e.name == cust.name:
            return eid
    return None


def run(case_id: str, txn, world: World) -> AgentResult:
    findings: list[Finding] = []
    # Finding IDs are derived from case_id + index, not a module-global counter,
    # so re-investigating the same case reproduces identical IDs every time —
    # required for a stable audit trail and for the evidence ledger to link
    # correctly (§14: agent outputs must be reproducible, not run-order-dependent).
    fid = 0
    def _next_fid() -> str:
        nonlocal fid
        fid += 1
        return f"F-{case_id}-{fid:03d}"

    sender = _sender_entity(world, txn)
    ben = txn.beneficiary_id
    rels = world.relationships  # World normalises this to a list

    def directors_of(eid):
        return {r.src for r in rels if r.relationship_type == "director_of" and r.tgt == eid}

    if sender and ben:
        shared = directors_of(sender) & directors_of(ben)
        for d in shared:
            confs = [r.confidence for r in rels if r.relationship_type == "director_of"
                     and r.src == d and r.tgt in (sender, ben)]
            findings.append(Finding(
                id=_next_fid(), type="relationship", severity=Severity.MEDIUM,
                description=f"Common director detected: {world.entity(d).name} directs both "
                            f"{world.entity(sender).name} and {world.entity(ben).name}.",
                confidence=min(confs) if confs else 0.8, nodes=[d, sender, ben]))

    ubo = next((r for r in rels if r.relationship_type == "beneficial_owner_of" and r.tgt == ben), None)
    if ubo:
        owner = world.entity(ubo.src)
        findings.append(Finding(
            id=_next_fid(), type="ownership_chain", severity=Severity.MEDIUM,
            description=f"Beneficiary is owned through a further jurisdiction: {owner.name} "
                        f"({owner.country}) is recorded as beneficial owner of {world.entity(ben).name}.",
            confidence=ubo.confidence, nodes=[ubo.src, ben]))

    worst = max((SEVERITY_SCORE[f.severity] for f in findings), default=0.0)
    return AgentResult(
        agent="entity_intelligence", case_id=case_id, dimension="entity",
        severity=band_from_score(worst), findings=findings,
        unknowns=["Beneficial ownership has not been independently verified."] if ubo else [],
        recommended_actions=["Verify beneficial ownership.", "Assess independence of the counterparty relationship."] if findings else [],
        extra={"note": "A detected relationship is not evidence of wrongdoing. Additional due diligence recommended."},
    )
