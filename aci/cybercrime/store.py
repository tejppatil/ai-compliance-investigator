"""
In-memory state for the Cyber Crime module: officers, cases, the live
transaction buffer, and the WebSocket broadcast loop.

Deliberately NOT persisted to SQLite like the compliance module's
InvestigationCase — this module's whole point is live, continuously
regenerating stream data (the same way the compliance module's demo
transaction queue is an in-memory World seeded fresh each process start, not
a database table). Restarting the API resets the live feed and case
history, same posture as restarting a monitoring dashboard.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from aci.cybercrime.data import OFFICERS, seed_cases, seed_geo_incidents, seed_graph
from aci.cybercrime.models import CaseEvent, CyberCase, GeoIncident, LiveTransaction, Officer
from aci.cybercrime.simulator import TransactionSimulator

TICK_SECONDS = 2.5
FEED_BUFFER = 200


class CyberStore:
    def __init__(self):
        self.officers: dict[str, Officer] = {o.officer_id: o for o in OFFICERS}
        self.cases: dict[str, CyberCase] = seed_cases()
        self.geo_incidents: list[GeoIncident] = seed_geo_incidents()
        self.recent_transactions: list[LiveTransaction] = []
        self.simulator = TransactionSimulator()
        self._subscribers: list[asyncio.Queue] = []
        self._task: asyncio.Task | None = None

    # ── live feed ────────────────────────────────────────────────────────
    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._broadcast_loop())

    async def _broadcast_loop(self) -> None:
        while True:
            txn = self.simulator.tick()
            self.recent_transactions.append(txn)
            del self.recent_transactions[:-FEED_BUFFER]
            for q in list(self._subscribers):
                q.put_nowait(txn)
            await asyncio.sleep(TICK_SECONDS)

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=50)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        if q in self._subscribers:
            self._subscribers.remove(q)

    # ── case actions (human-triggered, always logged) ──────────────────
    def freeze_hop(self, tx_id: str, officer_name: str) -> dict:
        txn = next((t for t in self.recent_transactions if t.tx_id == tx_id), None)
        if not txn:
            raise KeyError(f"unknown transaction {tx_id}")
        case = self._case_for_account(txn.destination_account) or self._case_for_account(txn.source_account)
        action = f"{officer_name} triggered a HOLDING FREEZE on {txn.destination_account} (transaction {tx_id})."
        if case:
            if txn.destination_account in case.layering_path:
                idx = case.layering_path.index(txn.destination_account)
                if idx not in case.frozen_hops:
                    case.frozen_hops.append(idx)
            case.history.append(CaseEvent(actor=officer_name, action=action))
        return {"tx_id": tx_id, "frozen_account": txn.destination_account, "case_id": case.case_id if case else None,
               "action": action}

    def freeze_case_hop(self, case_id: str, hop_index: int, officer_name: str) -> CyberCase:
        """Freezes a specific hop in a KNOWN case's layering path directly —
        distinct from freeze_hop(), which freezes whatever a live feed
        transaction happens to touch. This is what the IO Case Ops view uses:
        the case's layering path is static/known in advance, so there's no
        live tx_id to key off, but the freeze is just as real (logged,
        officer-attributed, reflected in frozen_hops)."""
        case = self.cases.get(case_id)
        if not case:
            raise KeyError(f"unknown case {case_id}")
        if not (0 <= hop_index < len(case.layering_path)):
            raise ValueError(f"hop_index {hop_index} out of range for {case_id}")
        if hop_index not in case.frozen_hops:
            case.frozen_hops.append(hop_index)
        account = case.layering_path[hop_index]
        case.history.append(CaseEvent(actor=officer_name,
                                      action=f"{officer_name} triggered a HOLDING FREEZE on {account} (hop {hop_index + 1} of {case_id})."))
        return case

    def escalate_case(self, case_id: str, officer_name: str, note: str = "") -> CyberCase:
        case = self.cases.get(case_id)
        if not case:
            raise KeyError(f"unknown case {case_id}")
        case.escalation_level = 1
        case.status = "Escalated to Nodal"
        action = f"{officer_name} escalated {case_id} to the Nodal / Escalation Lead Officer." + (f' Note: "{note}"' if note else "")
        case.history.append(CaseEvent(actor=officer_name, action=action))
        if case.assigned_officer_id and case.assigned_officer_id in self.officers:
            self.officers[case.assigned_officer_id].status = "Escalated to Nodal"
            self.officers[case.assigned_officer_id].last_action = f"Escalated {case_id}"
            self.officers[case.assigned_officer_id].last_action_at = datetime.now(timezone.utc)
        return case

    def transfer_case(self, case_id: str, new_officer_id: str, actor_name: str) -> CyberCase:
        case = self.cases.get(case_id)
        officer = self.officers.get(new_officer_id)
        if not case or not officer:
            raise KeyError("unknown case or officer")
        old_officer_id = case.assigned_officer_id
        case.assigned_officer_id = new_officer_id
        case.history.append(CaseEvent(actor=actor_name, action=f"Ownership transferred to {officer.name} ({officer.badge_id})."))
        officer.assigned_case_id = case_id
        officer.status = "Active Investigation"
        officer.last_action = f"Assumed ownership of {case_id}"
        officer.last_action_at = datetime.now(timezone.utc)
        if old_officer_id and old_officer_id in self.officers and old_officer_id != new_officer_id:
            prev = self.officers[old_officer_id]
            if prev.assigned_case_id == case_id:
                prev.assigned_case_id = None
                prev.status = "Available"
        return case

    def _case_for_account(self, account: str) -> CyberCase | None:
        return next((c for c in self.cases.values() if account in c.layering_path), None)

    def graph_for_case(self, case_id: str):
        if case_id not in self.cases:
            raise KeyError(f"unknown case {case_id}")
        nodes, edges = seed_graph(case_id)
        return nodes, edges


STORE = CyberStore()
