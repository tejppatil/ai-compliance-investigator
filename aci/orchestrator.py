"""
Case Orchestrator (§6, §14).

A controlled, ordered pipeline (state-machine style) — preferable to unrestricted
autonomous agents. Each step writes to the audit trail. The pipeline stops at
`pending_human_review`; it never decides.
"""
from __future__ import annotations

from datetime import timedelta

from aci import config
from aci.agents import (compliance_agent, document_agent, entity_agent,
                        investigation_agent, kyc_agent, risk_agent, sanctions_agent,
                        transaction_agent)
from aci.data.synthetic import World
from aci.models import AuditEntry, InvestigationCase, utcnow

ESCALATION_TEAM = "Escalation Team — Senior Compliance"
ESCALATION_ASSIGNEE = "R. Menon, Senior Compliance Officer (MLRO)"

TIER1_DECISIONS = {"close", "info", "edd", "escalate"}
TIER2_DECISIONS = {"senior_close", "senior_override", "senior_return"}


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

    # After Entity Intelligence (so related parties it surfaced get screened
    # too) and before Compliance RAG (so retrieval can react to a hit).
    s = sanctions_agent.run(case_id, txn, world, entity_result=e)
    _sanctions_audit(audit, s)

    c = compliance_agent.run(case_id, txn, world, transaction_result=t, sanctions_result=s)
    audit.append(AuditEntry(actor="system", action=f"Compliance RAG retrieved {len(c.regulatory)} control(s) with provenance"))

    d = document_agent.run(case_id, txn, world)
    audit.append(AuditEntry(actor="system", action=f"Documentation check completed — severity {d.severity.value.upper()}"))

    k = kyc_agent.run(case_id, txn, world)
    audit.append(AuditEntry(actor="system", action=f"KYC completeness check completed — {'complete' if k.extra.get('complete') else 'issue(s) found'}"))

    results = {"transaction": t, "entity": e, "regulatory": c, "documentation": d, "kyc": k, "sanctions": s}
    risk = risk_agent.run(case_id, txn, results, customer)
    floor_note = f" — RAISED to {risk.band.value.upper()} by sanctions floor" if risk.sanctions_floor_applied else ""
    audit.append(AuditEntry(actor="system", action=f"Risk engine aggregated findings — {risk.band.value.upper()} (score {risk.score:.2f}, confidence {risk.confidence:.2f}){floor_note}"))

    narrative, evidence, graph, unknowns, actions = investigation_agent.run(
        txn, world, results, risk, use_ai_narrative=use_ai_narrative)
    audit.append(AuditEntry(actor="system", action=f"Investigation Agent assembled {case_id} — narrative source: {narrative.source}"))
    if narrative.suggested_action:
        # Logged so the record shows what the AI suggested ALONGSIDE what the
        # human actually decided — the pair is what makes AI recommendations
        # auditable and calibratable over time. Explicitly marked as a
        # suggestion so it can never be mistaken for the case outcome.
        audit.append(AuditEntry(
            actor="system",
            action=f'AI SUGGESTED (not a decision): "{narrative.suggested_action}"',
            details={"suggested_action": narrative.suggested_action, "source": narrative.source}))
    audit.append(AuditEntry(actor="system", action="Case ready — awaiting human decision"))

    return InvestigationCase(
        case_id=case_id, transaction_id=transaction_id, priority=risk.band,
        transaction=txn, customer=customer, agent_results=[t, e, s, c, d, k],
        risk=risk, evidence=evidence, graph=graph, narrative=narrative,
        unknowns=unknowns, recommended_actions=actions, audit=audit,
        sanctions_status=s.extra.get("confirmed_hit") and "hit"
                        or (s.extra.get("possible_match") and "possible" or "clear"),
    )


def _sanctions_audit(audit: list[AuditEntry], s) -> None:
    """A screening result is audit-worthy whichever way it goes: a clear is a
    positive assertion that screening ran and found nothing, which is exactly
    what an auditor needs to see later. Recording only hits would leave "was
    this even screened?" unanswerable."""
    if s.extra.get("confirmed_hit"):
        names = "; ".join(f.description.split(":", 1)[1].strip() for f in s.findings if f.type == "sanctions_hit")
        action = f"Sanctions screening: CONFIRMED MATCH — {names}"
    elif s.extra.get("possible_match"):
        action = f"Sanctions screening: {len(s.findings)} possible match(es) below the confirmed threshold — human confirmation required"
    else:
        action = f"Sanctions screening: no match — {s.extra.get('subject_count', 0)} subject(s) screened against {len(s.extra.get('lists_screened', []))} list(s)"
    audit.append(AuditEntry(actor="system", action=action,
                            details={"confirmed_hit": bool(s.extra.get("confirmed_hit")),
                                    "possible_match": bool(s.extra.get("possible_match")),
                                    "screened": s.extra.get("screened", [])}))


def record_human_decision(case: InvestigationCase, actor: str, decision: str,
                          note: str = "", role: str = "officer") -> InvestigationCase:
    """The ONLY place a decision enters the system (§13) — now a two-tier
    control. Tier 1 (escalation_level 0): either persona can close, request
    info, request EDD, or escalate to the named senior reviewer with an SLA.
    Tier 2 (escalation_level 1, awaiting senior review): ONLY role="senior"
    may decide — a tier-1 officer's attempt is rejected here, not just hidden
    in the UI, so the two-person control is real rather than cosmetic."""
    if case.escalation_level == 1:
        if role != "senior":
            raise PermissionError(
                f"Case {case.case_id} is escalated to {case.assigned_to} — only the assigned "
                "senior reviewer may decide it; a tier-1 officer cannot re-decide an escalated case.")
        if decision not in TIER2_DECISIONS:
            raise ValueError(f"Unknown senior decision '{decision}'; expected one of {sorted(TIER2_DECISIONS)}.")

        if decision == "senior_return":
            action = f"Senior Compliance Officer returned case for further evidence — note: \"{note}\"" if note else \
                "Senior Compliance Officer returned case for further evidence."
            case.escalation_level = 0
            case.status = "pending_human_review"
            case.assigned_team = None
            case.assigned_to = None
            case.sla_due_at = None
        else:
            verb = "approved the AI risk assessment and closed" if decision == "senior_close" else \
                   "OVERRODE the AI risk assessment and closed"
            action = f"Senior Compliance Officer {verb} the case" + (f' — note: "{note}"' if note else "")
            case.status = "closed"
            # 2, not 1: "resolved" is distinct from "awaiting" so the
            # Escalation Queue (db.list_escalations filters level == 1) stops
            # showing a case the moment the senior actually decides it.
            case.escalation_level = 2
        case.audit.append(AuditEntry(actor="human", action=action,
                                     details={"decision": decision, "note": note, "role": "senior"}))
        return case

    if decision not in TIER1_DECISIONS:
        raise ValueError(f"Unknown decision '{decision}'; expected one of {sorted(TIER1_DECISIONS)}.")

    action = f"Compliance officer decision: {decision}" + (f' — note: "{note}"' if note else "")
    case.audit.append(AuditEntry(actor="human", action=action, details={"decision": decision, "note": note, "role": role}))

    if decision == "escalate":
        case.escalation_level = 1
        case.status = "escalated"
        case.assigned_team = ESCALATION_TEAM
        case.assigned_to = ESCALATION_ASSIGNEE
        case.sla_due_at = utcnow() + timedelta(hours=config.ESCALATION_SLA_HOURS)
        case.audit.append(AuditEntry(
            actor="system",
            action=f"Case assigned to {ESCALATION_ASSIGNEE} — SLA due {case.sla_due_at.strftime('%Y-%m-%d %H:%M UTC')}",
            details={"assigned_team": ESCALATION_TEAM, "assigned_to": ESCALATION_ASSIGNEE,
                    "sla_due_at": case.sla_due_at.isoformat()}))
    else:
        case.status = {"close": "closed"}.get(decision, "in_review")
    return case
