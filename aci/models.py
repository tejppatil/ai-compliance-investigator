"""
Shared data contracts (§14, §15, §22).

Every agent returns the SAME predictable shape so the orchestrator, risk agent
and investigation agent can compose outputs without special-casing each source.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Severity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


# Numeric weight of a severity band. Used by the (deterministic) risk engine.
SEVERITY_SCORE: dict[Severity, float] = {
    Severity.HIGH: 1.0,
    Severity.MEDIUM: 0.6,
    Severity.LOW: 0.25,
    Severity.NONE: 0.0,
}


def band_from_score(score: float) -> Severity:
    if score >= 0.70:
        return Severity.HIGH
    if score >= 0.40:
        return Severity.MEDIUM
    if score > 0.0:
        return Severity.LOW
    return Severity.NONE


# ── Domain records (mirror the §15 data model) ──────────────────────────────
class Customer(BaseModel):
    customer_id: str
    name: str
    country: str
    industry: str
    risk_profile: str = "standard"
    onboarded: str
    # Explicit link to this customer's corporate entity record — resolving the
    # sender side of a transaction by name match is fragile once names diverge
    # (e.g. bulk-generated "SynthCorp N" vs "SenderCo N"); an id link is not.
    entity_id: Optional[str] = None


class Transaction(BaseModel):
    transaction_id: str
    customer_id: str
    amount: int
    currency: str = "INR"
    source_country: str
    destination_country: str
    ultimate_destination: str
    beneficiary_id: str
    beneficiary_registered: str
    timestamp: str
    purpose: str
    route: list[str]
    # ground-truth label — EVALUATION ONLY, never passed to any agent (§19)
    scenario_type: str = "unknown"


class Entity(BaseModel):
    entity_id: str
    name: str
    entity_type: str
    country: str
    registered: Optional[str] = None
    directors: list[str] = Field(default_factory=list)


class Relationship(BaseModel):
    src: str
    tgt: str
    relationship_type: str
    confidence: float
    source: str


class Document(BaseModel):
    transaction_id: str
    doc_type: str
    narrative: str
    amount: int
    currency: str = "INR"


# ── Agent output contract ───────────────────────────────────────────────────
class Signal(BaseModel):
    type: str
    severity: Severity
    explanation: str
    metric: Optional[str] = None


class Finding(BaseModel):
    id: str
    type: str
    severity: Severity
    description: str
    confidence: float = 0.75
    evidence_ids: list[str] = Field(default_factory=list)
    nodes: list[str] = Field(default_factory=list)


class RegulatoryHit(BaseModel):
    id: str
    title: str
    regulator: str
    jurisdiction: str
    section: str
    summary: str
    why: str
    score: float = 0.0
    # Provenance a compliance officer can actually check (§16, §17): every
    # citation must resolve to a real document, not just a KB row id.
    source_url: str = ""
    publication_date: str = ""
    document_version: str = ""


class Evidence(BaseModel):
    id: str
    source_type: str
    source_reference: str
    content: str
    timestamp: datetime = Field(default_factory=utcnow)


class AgentResult(BaseModel):
    """The uniform contract every agent returns (§14)."""
    agent: str
    case_id: str
    status: str = "completed"
    dimension: str
    severity: Severity = Severity.NONE
    signals: list[Signal] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    regulatory: list[RegulatoryHit] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)


class RiskRow(BaseModel):
    key: str
    label: str
    weight: float
    severity: Severity
    contribution: float
    # Traceability: which specific signal/finding IDs produced this severity —
    # "why HIGH" must resolve to concrete evidence, not just a number (§15, §18).
    source_refs: list[str] = Field(default_factory=list)


class RiskAssessment(BaseModel):
    rows: list[RiskRow]
    score: float
    band: Severity
    confidence: float
    # Set when a sanctions match forced the band above what the weighted rows
    # alone produce (aci/agents/risk_agent.py explains why screening is a floor
    # rather than a seventh weighted dimension). Holds the human-readable
    # reason so the UI never shows a band the rows can't account for without
    # saying why.
    sanctions_floor_applied: Optional[str] = None


class Narrative(BaseModel):
    source: str = "template"  # "ai" | "template"
    what_happened: str
    why_unusual: str
    who_involved: str
    conclusion: str


class AuditEntry(BaseModel):
    timestamp: datetime = Field(default_factory=utcnow)
    actor: str
    action: str
    details: dict[str, Any] = Field(default_factory=dict)


class InvestigationCase(BaseModel):
    case_id: str
    transaction_id: str
    priority: Severity
    status: str = "pending_human_review"
    transaction: Transaction
    customer: Customer
    agent_results: list[AgentResult]
    risk: RiskAssessment
    evidence: list[Evidence]
    graph: dict[str, Any]
    narrative: Narrative
    unknowns: list[str]
    recommended_actions: list[str]
    audit: list[AuditEntry]
    created_at: datetime = Field(default_factory=utcnow)
    # Two-tier escalation (§23-style Senior Compliance Officer review, see
    # aci/orchestrator.py record_human_decision). 0 = never escalated,
    # 1 = escalated and awaiting a senior decision, 2 = escalated and resolved.
    escalation_level: int = 0
    assigned_team: Optional[str] = None
    assigned_to: Optional[str] = None
    sla_due_at: Optional[datetime] = None
    # "hit" | "possible" | "clear" — denormalised out of agent_results onto the
    # case so the triage queue and escalation views can filter/rank on it
    # without deserialising every case's full JSON blob (same reason
    # escalation_level is a real column in db/schema.sql).
    sanctions_status: str = "clear"
