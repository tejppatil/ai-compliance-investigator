"""
API layer (§22).

    GET  /api/transactions              list the demo queue
    POST /api/investigations            run an investigation for a transaction
    GET  /api/investigations            list all persisted cases (dashboard)
    GET  /api/investigations/{case_id}  fetch a case
    GET  /api/investigations/{case_id}/findings
    GET  /api/investigations/{case_id}/evidence
    GET  /api/investigations/{case_id}/graph
    POST /api/investigations/{case_id}/review   record the human decision
    GET  /api/regulations/search?q=...  query the regulatory KB
    GET  /api/audit/{case_id}
    GET  /api/audit/{case_id}/verify     tamper-evident hash-chain check
    GET  /api/audit                      recent activity across all cases
    GET  /api/escalations                 cases awaiting senior review
    GET  /api/network-insights            entities shared across different customers' cases
    GET  /api/risk-methodology            RBA weights, policy, dimension descriptions
    GET  /api/rules                       the full detection-rule catalogue
    POST /api/transactions                submit a new transaction for investigation
    GET  /api/dashboard                  aggregate KPIs for the main dashboard
    GET  /api/status                     local-model / RAG provenance

SQLite-backed (aci/db.py) — cases and the audit trail survive a restart. No
external services required; the network is only ever touched, if at all, by
the local Ollama process on localhost (aci/llm.py).
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from aci import config, db, llm
from aci.agents.risk_agent import _RISK_DESCRIPTIONS, _RISK_LABELS
from aci.data.synthetic import seed_world
from aci.models import Document, Entity, Transaction
from aci.orchestrator import investigate, record_human_decision
from aci.rag.retriever import Retriever
from aci.rules_catalog import catalog as rules_catalog

app = FastAPI(title="AI Compliance Investigator", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

WORLD = seed_world()
RETRIEVER = Retriever()


@app.on_event("startup")
def _startup() -> None:
    db.init_db()
    RETRIEVER.ensure_dense_index()  # best-effort; no-op if Ollama isn't reachable


class InvestigateReq(BaseModel):
    transaction_id: str


class ReviewReq(BaseModel):
    actor: str = "compliance.officer"
    decision: str  # tier 1: close|info|edd|escalate — tier 2: senior_close|senior_override|senior_return
    note: str = ""
    role: str = "officer"  # "officer" | "senior" — enforced server-side, not just hidden in the UI


class NewTransactionReq(BaseModel):
    """Submits a transaction for an EXISTING demo customer to a NEW
    beneficiary entity created on the spot — proves the pipeline handles a
    transaction nobody staged in advance, not just the fixed demo queue. The
    beneficiary is genuinely newly registered (today's date), so a
    new_counterparty signal firing on it is real, not scripted."""
    customer_id: str
    amount: int
    beneficiary_name: str
    beneficiary_country: str
    destination_country: str
    ultimate_destination: Optional[str] = None
    purpose: str = "General trade settlement"
    route: Optional[list[str]] = None
    document_narrative: Optional[str] = None
    document_amount: Optional[int] = None


@app.get("/api/customers")
def list_customers():
    """Existing demo customers — used by the New Transaction form's dropdown
    (submitting for an EXISTING customer to a newly-created beneficiary; see
    POST /api/transactions)."""
    return [{"customer_id": c.customer_id, "name": c.name, "country": c.country, "risk_profile": c.risk_profile}
            for c in WORLD.customers.values()]


@app.get("/api/transactions")
def list_transactions():
    return [{"transaction_id": t.transaction_id, "customer": WORLD.customer(t.customer_id).name,
             "amount": t.amount, "route": t.route, "purpose": t.purpose}
            for t in WORLD.transactions.values()]


@app.post("/api/transactions")
def create_transaction(req: NewTransactionReq):
    """Adds a transaction to the shared in-memory WORLD — the same object
    every other endpoint reads from — so it's immediately investigable via
    the normal POST /api/investigations with no other backend change."""
    if req.customer_id not in WORLD.customers:
        raise HTTPException(404, "unknown customer")
    customer = WORLD.customer(req.customer_id)

    idx = len(WORLD.transactions) + 1
    tid = f"TX-NEW{idx:03d}"
    while tid in WORLD.transactions:
        idx += 1
        tid = f"TX-NEW{idx:03d}"
    eid = f"E-{tid}"

    now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    route = req.route or [customer.country, req.destination_country]
    ultimate = req.ultimate_destination or req.destination_country

    WORLD.entities[eid] = Entity(entity_id=eid, name=req.beneficiary_name, entity_type="company",
                                 country=req.beneficiary_country, registered=today)
    WORLD.transactions[tid] = Transaction(
        transaction_id=tid, customer_id=req.customer_id, amount=req.amount,
        source_country=customer.country, destination_country=req.destination_country,
        ultimate_destination=ultimate, beneficiary_id=eid, beneficiary_registered=today,
        timestamp=now.isoformat(), purpose=req.purpose, route=route, scenario_type="user_submitted")
    if req.document_narrative:
        WORLD.documents[tid] = Document(transaction_id=tid, doc_type="invoice",
                                        narrative=req.document_narrative,
                                        amount=req.document_amount or req.amount)
    return {"transaction_id": tid}


@app.post("/api/investigations")
def create_investigation(req: InvestigateReq):
    if req.transaction_id not in WORLD.transactions:
        raise HTTPException(404, "unknown transaction")
    case = investigate(req.transaction_id, WORLD)
    db.save_case(case)
    return case


@app.get("/api/investigations")
def list_investigations():
    return db.list_cases()


def _get(case_id: str):
    case = db.get_case(case_id)
    if not case:
        raise HTTPException(404, "unknown case — run POST /api/investigations first")
    return case


@app.get("/api/investigations/{case_id}")
def get_case(case_id: str):
    return _get(case_id)


@app.get("/api/investigations/{case_id}/findings")
def get_findings(case_id: str):
    case = _get(case_id)
    return [f for r in case.agent_results for f in r.findings]


@app.get("/api/investigations/{case_id}/evidence")
def get_evidence(case_id: str):
    return _get(case_id).evidence


@app.get("/api/investigations/{case_id}/graph")
def get_graph(case_id: str):
    return _get(case_id).graph


@app.post("/api/investigations/{case_id}/review")
def review(case_id: str, req: ReviewReq):
    try:
        case = record_human_decision(_get(case_id), req.actor, req.decision, req.note, req.role)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.save_case(case)
    return {"status": case.status, "escalation_level": case.escalation_level,
           "assigned_to": case.assigned_to, "sla_due_at": case.sla_due_at, "audit": case.audit}


@app.get("/api/regulations/search")
def search_regs(q: str, k: int = 5):
    return RETRIEVER.search(q, k=k)


@app.get("/api/regulations")
def list_regulations():
    """The full curated knowledge base, for browsing (not search-ranked) —
    every entry is a real, source-linked regulatory document (see
    aci/rag/knowledge_base.py header for how each was verified)."""
    return RETRIEVER.kb


@app.get("/api/audit/{case_id}")
def get_audit(case_id: str):
    return db.get_audit_log(case_id)


@app.get("/api/audit/{case_id}/verify")
def verify_audit(case_id: str):
    """Recomputes the SHA-256 hash chain over this case's audit trail and
    confirms every entry matches — a real integrity check, not a claim."""
    return db.verify_audit_chain(case_id)


@app.get("/api/audit")
def get_recent_audit(limit: int = 15):
    """Recent activity across ALL cases — the dashboard's live feed."""
    return db.recent_audit(limit)


@app.get("/api/escalations")
def get_escalations():
    """Cases currently assigned to the senior reviewer (Escalation Queue)."""
    return db.list_escalations()


@app.get("/api/network-insights")
def get_network_insights():
    """Entities (directors/beneficial owners/counterparties) appearing across
    MULTIPLE different customers' persisted cases — a lightweight, no-graph-
    database version of shared-infrastructure/network detection, computed
    over evidence graphs already persisted."""
    return db.network_insights()


@app.get("/api/risk-methodology")
def risk_methodology():
    """Real backend config for the Risk-Based Approach page — nothing here is
    hardcoded in the frontend."""
    dimensions = [
        {"key": key, "label": _RISK_LABELS[key], "description": _RISK_DESCRIPTIONS[key], "weight": weight}
        for key, weight in config.RISK_WEIGHTS.items()
    ]
    return {
        "dimensions": dimensions,
        "customer_risk_severity": {k: v.value for k, v in config.CUSTOMER_RISK_SEVERITY.items()},
        "risk_policy": config.RISK_POLICY,
        "escalation_sla_hours": config.ESCALATION_SLA_HOURS,
    }


@app.get("/api/rules")
def get_rules():
    """The full detection-rule catalogue — every deterministic check this
    system actually runs, with its real threshold from aci/config.py."""
    return rules_catalog()


@app.get("/api/dashboard")
def dashboard():
    """Aggregate KPIs for the main dashboard — computed from persisted cases,
    not hardcoded. Everything here is real backend/database output."""
    cases = db.list_cases()
    escalations = db.list_escalations()
    by_priority = Counter(c["priority"] for c in cases)
    by_status = Counter(c["status"] for c in cases)
    return {
        "total_transactions": len(WORLD.transactions),
        "total_investigations": len(cases),
        "high_priority_open": sum(1 for c in cases if c["priority"] == "high" and c["status"] != "closed"),
        "awaiting_human_review": by_status.get("pending_human_review", 0),
        "escalated": by_status.get("escalated", 0),
        "closed": by_status.get("closed", 0),
        "awaiting_senior_review": len(escalations),
        "overdue_escalations": sum(1 for e in escalations if e["overdue"]),
        "risk_distribution": {"high": by_priority.get("high", 0), "medium": by_priority.get("medium", 0),
                              "low": by_priority.get("low", 0), "none": by_priority.get("none", 0)},
        "recent_investigations": cases[:10],
        "recent_activity": db.recent_audit(8),
    }


@app.get("/api/status")
def status():
    """Local-model and RAG provenance the UI should show plainly, so nothing
    running is presented as more than it is (§7, §37)."""
    return {"ollama": llm.ollama_status(), "model_provenance": config.MODEL_PROVENANCE,
           "db_path": str(config.DB_PATH), "regulatory_kb_size": len(RETRIEVER.kb)}


@app.get("/")
def root():
    return {"service": "AI Compliance Investigator", "principle": "AI investigates. Human decides.",
            "docs": "/docs", "demo_transactions": list(WORLD.transactions)}
