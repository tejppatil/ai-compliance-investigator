"""
Agent 5 — Investigation Agent (§11, §12).

The most important agent: turns scattered findings into one coherent case —
what happened, why unusual, who is involved, what evidence, which controls,
what's unknown, what to investigate next — plus the evidence graph.
"""
from __future__ import annotations

from aci import llm
from aci.data.synthetic import World
from aci.models import Evidence, Narrative


def build_evidence(txn, world: World, results) -> list[Evidence]:
    """Mints sequential, collision-free evidence IDs. The previous version hand-
    numbered IDs (E-001..E-006, E-010..) which collided once >=4 entity findings
    were present and skipped others — evidence IDs must be unique because
    findings and the graph reference them directly."""
    t, e, c, d = results["transaction"], results["entity"], results["regulatory"], results["documentation"]
    ev: list[Evidence] = []
    _n = 0
    def _next_eid() -> str:
        nonlocal _n
        _n += 1
        return f"E-{_n:03d}"

    ev.append(Evidence(id=_next_eid(), source_type="transaction_db", source_reference=f"{txn.customer_id} history",
                       content=f"Historical median INR {t.extra['median']:,.0f}; this transaction is "
                               f"{t.extra['ratio']:.1f}x that."))
    ev.append(Evidence(id=_next_eid(), source_type="counterparty_record", source_reference=txn.beneficiary_id,
                       content=f"Beneficiary onboarded {txn.beneficiary_registered} "
                               f"(~{t.extra['counterparty_age_months']} months old)."))
    for f in e.findings:
        ev.append(Evidence(id=_next_eid(), source_type="entity_graph",
                           source_reference=" · ".join(f.nodes), content=f.description))
    doc = world.doc(txn.transaction_id)
    ev.append(Evidence(id=_next_eid(), source_type="document", source_reference=doc.doc_type if doc else "missing",
                       content=f'Invoice narrative: "{doc.narrative}"' if doc else "No supporting documentation."))
    for f in d.findings:
        ev.append(Evidence(id=_next_eid(), source_type="document_check",
                           source_reference=doc.doc_type if doc else "missing", content=f.description))
    for r in c.regulatory[:3]:
        ev.append(Evidence(id=_next_eid(), source_type="regulatory_source",
                           source_reference=f"{r.id} · {r.section}", content=f"{r.title} — {r.summary}"))
    return ev


def build_graph(txn, world: World, results) -> dict:
    nodes, edges = [], []
    ben = txn.beneficiary_id
    nodes.append({"id": txn.transaction_id, "label": txn.transaction_id, "kind": "transaction"})
    # sender entity
    sender = None
    cust = world.customer(txn.customer_id)
    for eid, en in world.entities.items():
        if en.name == cust.name:
            sender = eid
    if sender:
        nodes.append({"id": sender, "label": world.entity(sender).name, "kind": "entity"})
        edges.append({"src": txn.transaction_id, "tgt": sender, "label": "sender"})
    if world.entity(ben):
        nodes.append({"id": ben, "label": world.entity(ben).name, "kind": "entity"})
        edges.append({"src": txn.transaction_id, "tgt": ben, "label": "beneficiary"})
    doc = world.doc(txn.transaction_id)
    if doc:
        nodes.append({"id": f"DOC-{txn.transaction_id}", "label": "Invoice", "kind": "document"})
        edges.append({"src": txn.transaction_id, "tgt": f"DOC-{txn.transaction_id}", "label": "document"})
    for f in results["entity"].findings:
        for n in f.nodes:
            en = world.entity(n)
            if en and not any(x["id"] == n for x in nodes):
                nodes.append({"id": n, "label": en.name, "kind": "person" if en.entity_type == "individual" else "entity"})
        if f.type == "relationship" and len(f.nodes) == 3:
            d, s, b = f.nodes
            edges.append({"src": d, "tgt": s, "label": "directs", "hot": True})
            edges.append({"src": d, "tgt": b, "label": "directs", "hot": True})
        if f.type == "ownership_chain" and len(f.nodes) == 2:
            o, b = f.nodes
            edges.append({"src": o, "tgt": b, "label": "owns", "hot": True})
    return {"nodes": nodes, "edges": edges}


def run(txn, world: World, results, risk, use_ai_narrative: bool = True) -> tuple[Narrative, list[Evidence], dict, list[str], list[str]]:
    customer = world.customer(txn.customer_id)
    narrative = llm.ai_narrative(txn, customer, results, risk) if use_ai_narrative \
        else llm.template_narrative(txn, customer, results, risk)
    evidence = build_evidence(txn, world, results)
    graph = build_graph(txn, world, results)
    unknowns, actions = [], []
    for r in results.values():
        unknowns += r.unknowns
        actions += r.recommended_actions
    actions.append("Escalate per internal policy if concerns remain.")
    # dedupe, preserve order
    unknowns = list(dict.fromkeys(unknowns))
    actions = list(dict.fromkeys(actions))
    return narrative, evidence, graph, unknowns, actions
