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

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from aci import config
from aci.models import InvestigationCase

_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "db" / "schema.sql"


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
    return conn


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
            """INSERT INTO investigation_case (case_id, transaction_id, priority, status, created_at, updated_at, case_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(case_id) DO UPDATE SET
                 status = excluded.status, priority = excluded.priority,
                 updated_at = excluded.updated_at, case_json = excluded.case_json""",
            (case.case_id, case.transaction_id, case.priority.value, case.status,
             case.created_at.isoformat(), case.created_at.isoformat(), case_json),
        )
        already = {row["ts"] + row["actor"] + row["action"] for row in
                   conn.execute("SELECT ts, actor, action FROM audit_log WHERE case_id = ?", (case.case_id,))}
        for entry in case.audit:
            key = entry.timestamp.isoformat() + entry.actor + entry.action
            if key in already:
                continue
            conn.execute(
                "INSERT INTO audit_log (case_id, actor, action, ts, details) VALUES (?, ?, ?, ?, ?)",
                (case.case_id, entry.actor, entry.action, entry.timestamp.isoformat(), json.dumps(entry.details)),
            )


def get_case(case_id: str, db_path: Path | None = None) -> InvestigationCase | None:
    with _cursor(db_path) as conn:
        row = conn.execute("SELECT case_json FROM investigation_case WHERE case_id = ?", (case_id,)).fetchone()
        return InvestigationCase.model_validate_json(row["case_json"]) if row else None


def list_cases(db_path: Path | None = None) -> list[dict]:
    """Lightweight summaries for a case-queue dashboard — avoids deserialising
    the full JSON blob for every row just to list them."""
    with _cursor(db_path) as conn:
        rows = conn.execute(
            "SELECT case_id, transaction_id, priority, status, created_at FROM investigation_case ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_audit_log(case_id: str, db_path: Path | None = None) -> list[dict]:
    with _cursor(db_path) as conn:
        rows = conn.execute(
            "SELECT actor, action, ts, details FROM audit_log WHERE case_id = ? ORDER BY audit_id", (case_id,)
        ).fetchall()
        return [{**dict(r), "details": json.loads(r["details"] or "{}")} for r in rows]
