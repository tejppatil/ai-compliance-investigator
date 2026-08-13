"""
Case Orchestrator (§6, §14).

A controlled, ordered pipeline (state-machine style) — preferable to unrestricted
autonomous agents. Each step writes to the audit trail. The pipeline stops at
`pending_human_review`; it never decides.
"""
from __future__ import annotations

from aci.agents import (compliance_agent, document_agent, entity_agent,
                        investigation_agent, risk_agent, transaction_agent)
from aci.data.synthetic import World
from aci.models import AuditEntry, InvestigationCase


def investigate(transaction_id: str, world: World, use_ai_narrative: bool = True) -> InvestigationCase:
    """`use_ai_narrative=False` skips the local-LLM call and always uses the
    deterministic template — every dimension score is identical either way.
    Bulk evaluation over hundreds/thousands of synthetic cases (aci/evaluation)
    only needs the risk band, so it passes False rather than making one LLM
    call per case (§25: avoid unnecessary model calls)."""
    txn = world.transactions[transaction_id]
    customer = world.customer(txn.customer_id)
    case_id = f"CASE-{transaction_id.split('-')[-1]}"
    audit: list[AuditEntry] = [AuditEntry(actor="system", action=f"Transaction {transaction_id} received into investigation queue")]

    # 1-3 run conceptually in parallel; ordered here for a deterministic audit trail.
    t = transaction_agent.run(case_id, txn, world)
    audit.append(AuditEntry(actor="system", action=f"Transaction Intelligence completed — {len(t.signals)} signal(s), severity {t.severity.value.upper()}"))

    e = entity_agent.run(case_id, txn, world)
    audit.append(AuditEntry(actor="system", action=f"Entity Intelligence completed — {len(e.findings)} relationship finding(s)"))

    c = compliance_agent.run(case_id, txn, world, transaction_result=t)
    audit.append(AuditEntry(actor="system", action=f"Compliance RAG retrieved {len(c.regulatory)} control(s) with provenance"))

    d = document_agent.run(case_id, txn, world)
    audit.append(AuditEntry(actor="system", action=f"Documentation check completed — severity {d.severity.value.upper()}"))

    results = {"transaction": t, "entity": e, "regulatory": c, "documentation": d}
    risk = risk_agent.run(case_id, txn, results)
    audit.append(AuditEntry(actor="system", action=f"Risk engine aggregated findings — {risk.band.value.upper()} (score {risk.score:.2f}, confidence {risk.confidence:.2f})"))

    narrative, evidence, graph, unknowns, actions = investigation_agent.run(
        txn, world, results, risk, use_ai_narrative=use_ai_narrative)
    audit.append(AuditEntry(actor="system", action=f"Investigation Agent assembled {case_id} — narrative source: {narrative.source}"))
    audit.append(AuditEntry(actor="system", action="Case ready — awaiting human decision"))

    return InvestigationCase(
        case_id=case_id, transaction_id=transaction_id, priority=risk.band,
        transaction=txn, customer=customer, agent_results=[t, e, c, d],
        risk=risk, evidence=evidence, graph=graph, narrative=narrative,
        unknowns=unknowns, recommended_actions=actions, audit=audit,
    )


def record_human_decision(case: InvestigationCase, actor: str, decision: str, note: str = "") -> InvestigationCase:
    """The ONLY place a decision enters the system (§13)."""
    action = f"Compliance officer decision: {decision}" + (f' — note: "{note}"' if note else "")
    case.audit.append(AuditEntry(actor="human", action=action, details={"decision": decision, "note": note}))
    case.status = {"close": "closed", "escalate": "escalated"}.get(decision, "in_review")
    return case
