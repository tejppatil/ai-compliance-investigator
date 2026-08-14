"""
Local persistence (§15, §23).

A single SQLite file — no server to start, no separate service to run. The
previous version of this project shipped `db/schema.sql` as unused Postgres
DDL: a `docker-compose.yml` started a Postgres nothing ever connected to,
while the API held cases in a plain dict that emptied on every restart,
silently discarding the audit trail the blueprint requires. This module is
what actually gets used.

`case_to_row`/`row_to_case` round-trip the full pydantic `InvestigationCase`
as JSON — see db/schema.sql for why a JSON blob was chosen over a fully
normalised schema for a prototype at this scale. The audit trail is
additionally written to its own table so it can be queried/exported
independently of any single case.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from aci import config
from aci.models import InvestigationCase, utcnow

_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "db" / "schema.sql"

GENESIS_HASH = "0" * 64  # the "prev_hash" of the first audit entry for any case

# Columns added after each table's initial release. CREATE TABLE IF NOT EXISTS
# only helps a brand-new database; an existing data_local/aci.db from before a
# feature landed needs these ALTERed in, not recreated — recreating would
# silently drop every previously persisted case.
_MIGRATED_COLUMNS = {
    "investigation_case": [
        ("escalation_level", "INTEGER NOT NULL DEFAULT 0"),
        ("assigned_to", "TEXT"),
        ("sla_due_at", "TEXT"),
        # Denormalised from the case JSON for the same reason as
        # escalation_level: the triage queue ranks on it, and deserialising
        # every case's full blob to sort a list would be absurd.
        ("sanctions_status", "TEXT NOT NULL DEFAULT 'clear'"),
    ],
    "audit_log": [
        ("prev_hash", "TEXT"),
        ("entry_hash", "TEXT"),
    ],
}


def _entry_hash(prev_hash: str, case_id: str, actor: str, action: str, ts: str, details_json: str) -> str:
    """SHA-256 over the previous entry's hash plus this entry's own content —
    changing or reordering any past entry changes every hash after it, which
    is what makes the chain tamper-evident (verify_audit_chain below)."""
    payload = f"{prev_hash}|{case_id}|{actor}|{action}|{ts}|{details_json}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or config.DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    # Self-heal the schema rather than assuming startup already ran: the DB
    # file can be deleted, moved, or reset while the process is live (and a
    # long-running API shouldn't 500 forever afterwards). The schema uses
    # CREATE TABLE IF NOT EXISTS throughout, so this is a cheap no-op once
    # the tables exist.
    missing = conn.execute(
        "SELECT COUNT(*) AS n FROM sqlite_master WHERE type='table' AND name='investigation_case'"
    ).fetchone()["n"] == 0
    if missing:
        conn.executescript(_SCHEMA_PATH.read_text())
        conn.commit()
    else:
        _migrate_columns(conn)
    return conn


def _migrate_columns(conn: sqlite3.Connection) -> None:
    for table, columns in _MIGRATED_COLUMNS.items():
        existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
        for name, ddl in columns:
            if name not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")
    conn.commit()


def init_db(db_path: Path | None = None) -> None:
    """Explicit initialisation (called at API startup). _connect() also
    self-heals, so this is belt-and-braces rather than the only path."""
    _connect(db_path).close()


@contextmanager
def _cursor(db_path: Path | None = None):
    conn = _connect(db_path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def save_case(case: InvestigationCase, db_path: Path | None = None) -> None:
    """Upserts the full case, and appends any audit entries not already
    written to the standalone audit_log table (idempotent on re-save)."""
    with _cursor(db_path) as conn:
        case_json = case.model_dump_json()
        conn.execute(
            """INSERT INTO investigation_case
                 (case_id, transaction_id, priority, status, created_at, updated_at, case_json,
                  escalation_level, assigned_to, sla_due_at, sanctions_status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(case_id) DO UPDATE SET
                 status = excluded.status, priority = excluded.priority,
                 updated_at = excluded.updated_at, case_json = excluded.case_json,
                 escalation_level = excluded.escalation_level,
                 assigned_to = excluded.assigned_to, sla_due_at = excluded.sla_due_at,
                 sanctions_status = excluded.sanctions_status""",
            (case.case_id, case.transaction_id, case.priority.value, case.status,
             case.created_at.isoformat(), case.created_at.isoformat(), case_json,
             case.escalation_level, case.assigned_to,
             case.sla_due_at.isoformat() if case.sla_due_at else None,
             case.sanctions_status),
        )
        already = {row["ts"] + row["actor"] + row["action"] for row in
                   conn.execute("SELECT ts, actor, action FROM audit_log WHERE case_id = ?", (case.case_id,))}
        last = conn.execute(
            "SELECT entry_hash FROM audit_log WHERE case_id = ? ORDER BY audit_id DESC LIMIT 1", (case.case_id,)
        ).fetchone()
        prev_hash = (last["entry_hash"] if last and last["entry_hash"] else GENESIS_HASH)
        for entry in case.audit:
            ts = entry.timestamp.isoformat()
            key = ts + entry.actor + entry.action
            if key in already:
                continue
            details_json = json.dumps(entry.details)
            entry_hash = _entry_hash(prev_hash, case.case_id, entry.actor, entry.action, ts, details_json)
            conn.execute(
                "INSERT INTO audit_log (case_id, actor, action, ts, details, prev_hash, entry_hash) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (case.case_id, entry.actor, entry.action, ts, details_json, prev_hash, entry_hash),
            )
            prev_hash = entry_hash


def get_case(case_id: str, db_path: Path | None = None) -> InvestigationCase | None:
    with _cursor(db_path) as conn:
        row = conn.execute("SELECT case_json FROM investigation_case WHERE case_id = ?", (case_id,)).fetchone()
        return InvestigationCase.model_validate_json(row["case_json"]) if row else None


def list_cases(db_path: Path | None = None) -> list[dict]:
    """Lightweight summaries for a case-queue dashboard — avoids deserialising
    the full JSON blob for every row just to list them."""
    with _cursor(db_path) as conn:
        rows = conn.execute(
            "SELECT case_id, transaction_id, priority, status, created_at, escalation_level, "
            "sla_due_at, sanctions_status FROM investigation_case ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_audit_log(case_id: str, db_path: Path | None = None) -> list[dict]:
    with _cursor(db_path) as conn:
        rows = conn.execute(
            "SELECT actor, action, ts, details FROM audit_log WHERE case_id = ? ORDER BY audit_id", (case_id,)
        ).fetchall()
        return [{**dict(r), "details": json.loads(r["details"] or "{}")} for r in rows]


def verify_audit_chain(case_id: str, db_path: Path | None = None) -> dict:
    """Recomputes the SHA-256 hash chain for a case's audit trail and confirms
    every entry's stored hash matches what it should be given the entries
    before it. A tampered or reordered row breaks the chain from that point
    on — this is what makes the audit trail's integrity checkable rather than
    just claimed (§23)."""
    with _cursor(db_path) as conn:
        rows = conn.execute(
            """SELECT audit_id, actor, action, ts, details, prev_hash, entry_hash
               FROM audit_log WHERE case_id = ? ORDER BY audit_id""", (case_id,)
        ).fetchall()
        expected_prev = GENESIS_HASH
        for row in rows:
            details_json = row["details"] or "{}"
            computed = _entry_hash(row["prev_hash"] or GENESIS_HASH, case_id, row["actor"], row["action"], row["ts"], details_json)
            if row["prev_hash"] != expected_prev or row["entry_hash"] != computed:
                return {"verified": False, "entries": len(rows), "broken_at": row["audit_id"]}
            expected_prev = row["entry_hash"]
        return {"verified": True, "entries": len(rows), "broken_at": None}


def recent_audit(limit: int = 15, db_path: Path | None = None) -> list[dict]:
    """Most recent audit entries ACROSS all cases — the dashboard's "live
    activity" feed. Reads the existing audit_log table; no new writes."""
    with _cursor(db_path) as conn:
        rows = conn.execute(
            "SELECT case_id, actor, action, ts, details FROM audit_log ORDER BY audit_id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [{**dict(r), "details": json.loads(r["details"] or "{}")} for r in rows]


def network_insights(db_path: Path | None = None) -> list[dict]:
    """Cross-case network insight: does the same entity (director/beneficial
    owner/counterparty) appear in the evidence graph of cases belonging to
    DIFFERENT customers? entity_agent.py already finds shared directors
    within one transaction's sender/beneficiary pair — this extends the same
    idea across the whole case history, over data already persisted (no new
    agent inference, just a query across existing case_json graphs)."""
    with _cursor(db_path) as conn:
        rows = conn.execute("SELECT case_id, case_json FROM investigation_case").fetchall()

    by_entity: dict[str, list[dict]] = {}
    for row in rows:
        case = json.loads(row["case_json"])
        customer_id = case.get("customer", {}).get("customer_id")
        for node in case.get("graph", {}).get("nodes", []):
            if node.get("kind") not in ("entity", "person"):
                continue
            by_entity.setdefault(node["id"], []).append({
                "case_id": case["case_id"], "transaction_id": case["transaction_id"],
                "customer_id": customer_id, "entity_label": node["label"],
            })

    insights = []
    for entity_id, appearances in by_entity.items():
        customers = {a["customer_id"] for a in appearances}
        if len(customers) >= 2:
            insights.append({
                "entity_id": entity_id, "entity_label": appearances[0]["entity_label"],
                "customer_count": len(customers), "case_count": len(appearances),
                "cases": appearances,
            })
    insights.sort(key=lambda i: i["customer_count"], reverse=True)
    return insights


def list_escalations(db_path: Path | None = None) -> list[dict]:
    """Cases currently awaiting a senior decision (escalation_level = 1),
    for the Escalation Queue view. `overdue` is computed here so the
    frontend never has to compare timestamps itself."""
    with _cursor(db_path) as conn:
        rows = conn.execute(
            """SELECT case_id, transaction_id, priority, status, assigned_to, sla_due_at
               FROM investigation_case WHERE escalation_level = 1 ORDER BY sla_due_at"""
        ).fetchall()
        now = utcnow().isoformat()
        return [{**dict(r), "overdue": bool(r["sla_due_at"] and r["sla_due_at"] < now)} for r in rows]
