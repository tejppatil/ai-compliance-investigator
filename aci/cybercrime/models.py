"""Data contracts for the Cyber Crime module. Mirrors the style of aci/models.py
(pydantic, explicit fields, no untyped dicts crossing the API boundary) so the
two modules read as one system even though they're functionally separate."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Officer(BaseModel):
    officer_id: str
    name: str
    badge_id: str
    role: str  # "nodal" | "io" | "analyst"
    status: str = "Available"  # Active Investigation | Cold Case | Escalated to Nodal | Pending Freeze | Available
    assigned_case_id: Optional[str] = None
    last_action: str = "Signed on"
    last_action_at: datetime = Field(default_factory=utcnow)


class CaseEvent(BaseModel):
    ts: datetime = Field(default_factory=utcnow)
    actor: str
    action: str


class CyberCase(BaseModel):
    case_id: str
    title: str
    crime_type: str  # Phishing | Mule Network | Ransomware | Investment Fraud | Account Takeover
    severity: str  # low | medium | high | critical
    status: str = "Active Investigation"
    assigned_officer_id: Optional[str] = None
    escalation_level: int = 0  # 0 = none, 1 = escalated to Nodal
    source_account: str
    layering_path: list[str] = Field(default_factory=list)  # [source, mule1, mule2, cashout]
    frozen_hops: list[int] = Field(default_factory=list)  # indices into layering_path that are frozen
    amount: int
    currency: str = "INR"
    created_at: datetime = Field(default_factory=utcnow)
    history: list[CaseEvent] = Field(default_factory=list)


class LiveTransaction(BaseModel):
    tx_id: str
    ts: datetime = Field(default_factory=utcnow)
    source_account: str
    destination_account: str
    amount: int
    currency: str = "INR"
    channel: str  # NEFT | RTGS | IMPS | UPI | Crypto
    city: str
    lat: float
    lng: float
    hop_index: int = 0  # position within a layering chain; 0 = first hop from source
    case_id: Optional[str] = None  # set once a flagged transaction is attached to a case
    flagged: bool = False
    flag_reasons: list[str] = Field(default_factory=list)
    risk_score: int = 0  # 0-100, deterministic rule-engine output


class GeoIncident(BaseModel):
    incident_id: str
    lat: float
    lng: float
    city: str
    state: str
    crime_type: str
    severity: str  # low | medium | high | critical
    source: str  # "1930 Cybercrime Helpline" | "Bank Transfer Flag" | "OSINT / News"
    reported_at: datetime
    description: str


class GraphEntity(BaseModel):
    id: str
    type: str  # phone | social_handle | imei | bank_account | upi_id | crypto_wallet | ip_address | cell_tower | fir_report
    label: str
    confidence: float
    details: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    src: str
    tgt: str
    relationship_type: str
    confidence: float
