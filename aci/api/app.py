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
    GET  /api/dashboard                  aggregate KPIs for the main dashboard
    GET  /api/status                     local-model / RAG provenance

SQLite-backed (aci/db.py) — cases and the audit trail survive a restart. No
external services required; the network is only ever touched, if at all, by
the local Ollama process on localhost (aci/llm.py).
"""
from __future__ import annotations

from collections import Counter

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from aci import config, db, llm
from aci.data.synthetic import seed_world
from aci.orchestrator import investigate, record_human_decision
from aci.rag.retriever import Retriever

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
    decision: str  # close | info | edd | escalate
    note: str = ""


@app.get("/api/transactions")
def list_transactions():
    return [{"transaction_id": t.transaction_id, "customer": WORLD.customer(t.customer_id).name,
             "amount": t.amount, "route": t.route, "purpose": t.purpose}
            for t in WORLD.transactions.values()]


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
    case = record_human_decision(_get(case_id), req.actor, req.decision, req.note)
    db.save_case(case)
    return {"status": case.status, "audit": case.audit}


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


@app.get("/api/dashboard")
def dashboard():
    """Aggregate KPIs for the main dashboard — computed from persisted cases,
    not hardcoded. Everything here is real backend/database output."""
    cases = db.list_cases()
    by_priority = Counter(c["priority"] for c in cases)
    by_status = Counter(c["status"] for c in cases)
    return {
        "total_transactions": len(WORLD.transactions),
        "total_investigations": len(cases),
        "high_priority_open": sum(1 for c in cases if c["priority"] == "high" and c["status"] != "closed"),
        "awaiting_human_review": by_status.get("pending_human_review", 0),
        "escalated": by_status.get("escalated", 0),
        "closed": by_status.get("closed", 0),
        "risk_distribution": {"high": by_priority.get("high", 0), "medium": by_priority.get("medium", 0),
                              "low": by_priority.get("low", 0), "none": by_priority.get("none", 0)},
        "recent_investigations": cases[:10],
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
