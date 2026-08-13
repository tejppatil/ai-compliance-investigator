-- SQLite schema (Blueprint §15, §23). A single local file — no server to run,
-- no separate service to start. Applied automatically by aci/db.py on first
-- use; this file is the readable reference copy.
--
-- `investigation_case` stores the full case as JSON alongside the columns an
-- operator actually needs to query without deserialising (status, priority,
-- transaction_id). Findings/evidence/the graph are nested inside that JSON —
-- for this prototype's scale (one case per transaction, not a high-volume
-- production ledger) that is simpler and no less queryable than a fully
-- normalised finding/evidence table set, and avoids an ORM for its own sake.
-- `audit_log` is kept as its own table (in addition to being embedded in the
-- case JSON) specifically so "every investigation action, ever" can be
-- queried/exported independently of any single case (§23).

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS investigation_case (
    case_id         TEXT PRIMARY KEY,
    transaction_id  TEXT NOT NULL,
    priority        TEXT NOT NULL,          -- high | medium | low | none
    status          TEXT NOT NULL DEFAULT 'pending_human_review',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    case_json       TEXT NOT NULL           -- full InvestigationCase, JSON-serialised
);

CREATE TABLE IF NOT EXISTS audit_log (
    audit_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id    TEXT NOT NULL REFERENCES investigation_case(case_id),
    actor      TEXT NOT NULL,
    action     TEXT NOT NULL,
    ts         TEXT NOT NULL,
    details    TEXT                          -- JSON
);

CREATE INDEX IF NOT EXISTS idx_case_status ON investigation_case(status);
CREATE INDEX IF NOT EXISTS idx_case_priority ON investigation_case(priority);
CREATE INDEX IF NOT EXISTS idx_audit_case ON audit_log(case_id);
