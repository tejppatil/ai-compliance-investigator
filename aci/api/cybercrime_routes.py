"""
Cyber Crime & Financial Fraud Investigation module — REST + WebSocket routes.

    GET  /api/cyber/officers                  all officers, status, assignment
    GET  /api/cyber/cases                     all cases
    GET  /api/cyber/cases/{case_id}
    POST /api/cyber/cases/{case_id}/escalate  {"officer_name","note"}
    POST /api/cyber/cases/{case_id}/transfer  {"new_officer_id","actor_name"}
    POST /api/cyber/transactions/{tx_id}/freeze  {"officer_name"} — human-triggered, always logged
    GET  /api/cyber/transactions/recent?limit=
    GET  /api/cyber/geo-incidents?crime_type=&severity=&hours=
    GET  /api/cyber/graph/{case_id}
    WS   /ws/cyber/transactions                live transaction feed

Mounted into aci/api/app.py. Kept as its own router/module so this
law-enforcement-facing module stays clearly separate from the corporate AML
compliance API it's bolted onto (see aci/cybercrime/__init__.py).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from aci.cybercrime.store import STORE

router = APIRouter(prefix="/api/cyber", tags=["cybercrime"])


class EscalateReq(BaseModel):
    officer_name: str
    note: str = ""


class TransferReq(BaseModel):
    new_officer_id: str
    actor_name: str


class FreezeReq(BaseModel):
    officer_name: str


class FreezeHopReq(BaseModel):
    hop_index: int
    officer_name: str


@router.get("/officers")
def list_officers():
    return list(STORE.officers.values())


@router.get("/cases")
def list_cases():
    return list(STORE.cases.values())


@router.get("/cases/{case_id}")
def get_case(case_id: str):
    case = STORE.cases.get(case_id)
    if not case:
        raise HTTPException(404, "unknown case")
    return case


@router.post("/cases/{case_id}/escalate")
def escalate_case(case_id: str, req: EscalateReq):
    try:
        return STORE.escalate_case(case_id, req.officer_name, req.note)
    except KeyError as e:
        raise HTTPException(404, str(e))


@router.post("/cases/{case_id}/transfer")
def transfer_case(case_id: str, req: TransferReq):
    try:
        return STORE.transfer_case(case_id, req.new_officer_id, req.actor_name)
    except KeyError as e:
        raise HTTPException(404, str(e))


@router.post("/cases/{case_id}/freeze-hop")
def freeze_case_hop(case_id: str, req: FreezeHopReq):
    """Freezes a specific account in a case's known layering path — see
    CyberStore.freeze_case_hop for why this differs from the live-feed
    tx-based freeze below."""
    try:
        return STORE.freeze_case_hop(case_id, req.hop_index, req.officer_name)
    except KeyError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/transactions/{tx_id}/freeze")
def freeze_transaction(tx_id: str, req: FreezeReq):
    """A human clicking a button — never triggered automatically by the rule
    engine. Same human-in-the-loop boundary as the compliance module's
    'AI investigates, human decides.'"""
    try:
        return STORE.freeze_hop(tx_id, req.officer_name)
    except KeyError as e:
        raise HTTPException(404, str(e))


@router.get("/transactions/recent")
def recent_transactions(limit: int = 50):
    return STORE.recent_transactions[-limit:][::-1]


@router.get("/geo-incidents")
def geo_incidents(crime_type: str | None = None, severity: str | None = None, hours: int | None = None):
    rows = STORE.geo_incidents
    if crime_type:
        rows = [r for r in rows if r.crime_type == crime_type]
    if severity:
        rows = [r for r in rows if r.severity == severity]
    if hours:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        rows = [r for r in rows if r.reported_at >= cutoff]
    return rows


@router.get("/graph/{case_id}")
def graph_for_case(case_id: str):
    try:
        nodes, edges = STORE.graph_for_case(case_id)
    except KeyError as e:
        raise HTTPException(404, str(e))
    return {"nodes": nodes, "edges": edges}


def register_websocket(app) -> None:
    """Registered directly on `app` (not this router) so the path is exactly
    /ws/cyber/transactions regardless of router-prefix mounting details."""
    @app.websocket("/ws/cyber/transactions")
    async def cyber_transactions_ws(websocket: WebSocket):
        await websocket.accept()
        queue = STORE.subscribe()
        try:
            # Prime the client with recent history so a fresh connection
            # isn't staring at an empty feed until the next tick.
            for txn in STORE.recent_transactions[-20:]:
                await websocket.send_json(txn.model_dump(mode="json"))
            while True:
                txn = await queue.get()
                await websocket.send_json(txn.model_dump(mode="json"))
        except WebSocketDisconnect:
            pass
        finally:
            STORE.unsubscribe(queue)
