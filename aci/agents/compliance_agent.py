"""
Agent 3 — Compliance Intelligence / Regulatory RAG (§9, §16, §17).

Determines relevant controls by RETRIEVING from the knowledge base, never from
model memory. Every hit carries provenance and a "why relevant" line grounded
in the transaction's own signals. Retrieval is filtered to the transaction's
actual jurisdictions plus GIFT IFSC (the operating institution's home
regulator in this prototype's framing) and international (FATF) baseline
standards — a transaction touching a corridor this KB has no coverage for
gets an honest "insufficient information" result, not an irrelevant citation.
"""
from __future__ import annotations

from aci.agents import transaction_agent
from aci.data.synthetic import World
from aci.models import AgentResult, Severity
from aci.rag.retriever import Retriever

_RETRIEVER = Retriever()

# Country names as they appear in Transaction.route -> this KB's jurisdiction tags.
_COUNTRY_TO_JURISDICTION = {"India": "India", "UAE": "UAE", "Singapore": "Singapore"}

INSUFFICIENT_INFO = "Insufficient information in the configured regulatory knowledge base."


def _jurisdictions_for(txn) -> set[str]:
    return {"GIFT IFSC"} | {_COUNTRY_TO_JURISDICTION[c] for c in txn.route if c in _COUNTRY_TO_JURISDICTION}


def run(case_id: str, txn, world: World, retriever: Retriever | None = None,
        transaction_result: AgentResult | None = None) -> AgentResult:
    """`transaction_result` lets the orchestrator pass in the Transaction
    Intelligence output it already computed — recomputing the same
    deterministic statistics a second time on every case is wasted work."""
    retriever = retriever or _RETRIEVER
    t = transaction_result or transaction_agent.run(case_id, txn, world)
    signal_types = {s.type for s in t.signals}
    doc = world.doc(txn.transaction_id)

    boost = {"cross-border", "kyc", "reporting"}
    query_terms = ["cross border transaction due diligence"]
    why_map: dict[str, str] = {}

    if "amount_anomaly" in signal_types:
        boost |= {"high-value", "edd"}
        query_terms.append("high value large amount enhanced due diligence")
        why_map["IFSCA-AML-2022"] = "Amount is materially above the customer's own baseline and the counterparty is newly onboarded — meets the enhanced due diligence trigger."
    if "new_counterparty" in signal_types:
        boost |= {"edd"}
    if "structuring" in signal_types:
        boost |= {"structuring"}
        query_terms.append("repeated transfers just below reporting threshold structuring")
        why_map["IN-PMLA-S12"] = "Pattern of transfers clustering near/below the reporting threshold matches the statutory structuring criteria."
    if "rapid_movement" in signal_types:
        boost |= {"cross-border", "documentation"}
        query_terms.append("correspondent banking trade based money laundering layering")
        why_map["AE-CBUAE-GUIDANCE"] = "Elevated transaction velocity combined with multi-hop routing matches trade-based money-laundering / layering red flags."
    if len(txn.route) >= 3:
        boost |= {"beneficial-ownership"}
        query_terms.append("beneficial ownership layered structure jurisdiction chain")
        why_map["FATF-R24"] = "Beneficiary sits in a multi-jurisdiction ownership chain with an unverified ultimate beneficial owner."
    if doc and len(doc.narrative.split()) <= 3:
        boost |= {"documentation"}

    why_map.setdefault("IFSCA-AML-2022", "Baseline AML/CFT/KYC obligation applying to all customer transactions processed via GIFT IFSC.")
    why_map.setdefault("IN-RBI-LRS", "Value and outward routing meet the review criteria for cross-border remittance reporting.")
    why_map.setdefault("FATF-R16", "Cross-border wire transfer — originator/beneficiary transparency requirement applies.")

    jurisdictions = _jurisdictions_for(txn)
    hits = retriever.search(" ".join(query_terms), boost_tags=boost, k=5, jurisdictions=jurisdictions)
    for h in hits:
        h.why = why_map.get(h.id, "Retrieved as relevant to this transaction's attributes.")

    unknowns = ["Applicability of specific reporting obligations pending human confirmation."]
    if not hits:
        unknowns = [INSUFFICIENT_INFO]

    severity = Severity.HIGH if hits and ("edd" in boost or "structuring" in boost) else (Severity.MEDIUM if hits else Severity.LOW)
    return AgentResult(
        agent="compliance_intelligence", case_id=case_id, dimension="regulatory",
        severity=severity, regulatory=hits, unknowns=unknowns,
        recommended_actions=["Confirm applicable cross-border reporting obligation.",
                             "Escalate per internal policy if concerns remain."] if hits else
                            ["Escalate to a compliance officer for manual regulatory review — no matching KB coverage."],
        extra={"disclaimer": "Real, publicly issued regulatory documents — see source_url on each hit. Summaries are this project's own paraphrase, not quoted statute text.",
              "jurisdictions_searched": sorted(jurisdictions)},
    )
