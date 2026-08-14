"""
Seed data for the Cyber Crime module — entirely synthetic, same posture as
every other dataset in this project (see docs/DATASET_CARD.md): no real
person, account, or institution is represented. Coordinates are real city
locations (public geography), used only to make the heat map legible; the
incidents plotted on them are generated, not sourced from any actual report.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from aci.cybercrime.models import CaseEvent, CyberCase, GeoIncident, GraphEdge, GraphEntity, Officer

# name, state, lat, lng — real Indian city coordinates, used for map legibility only.
CITIES = [
    ("Mumbai", "Maharashtra", 19.0760, 72.8777),
    ("Delhi", "Delhi", 28.7041, 77.1025),
    ("Bengaluru", "Karnataka", 12.9716, 77.5946),
    ("Jamtara", "Jharkhand", 23.9600, 86.8000),
    ("Deoghar", "Jharkhand", 24.4823, 86.6947),
    ("Bharatpur", "Rajasthan", 27.2173, 77.4901),
    ("Nuh", "Haryana", 28.1109, 77.0025),
    ("Alwar", "Rajasthan", 27.5530, 76.6346),
    ("Hyderabad", "Telangana", 17.3850, 78.4867),
    ("Pune", "Maharashtra", 18.5204, 73.8567),
    ("Kolkata", "West Bengal", 22.5726, 88.3639),
    ("Chennai", "Tamil Nadu", 13.0827, 80.2707),
    ("Ahmedabad", "Gujarat", 23.0225, 72.5714),
    ("Jaipur", "Rajasthan", 26.9124, 75.7873),
    ("Lucknow", "Uttar Pradesh", 26.8467, 80.9462),
    ("Guwahati", "Assam", 26.1445, 91.7362),
    ("Bhopal", "Madhya Pradesh", 23.2599, 77.4126),
    ("Patna", "Bihar", 25.5941, 85.1376),
    ("Surat", "Gujarat", 21.1702, 72.8311),
    ("Indore", "Madhya Pradesh", 22.7196, 75.8577),
]

CRIME_TYPES = ["Phishing", "Mule Network", "Ransomware", "Investment Fraud", "Account Takeover"]
SEVERITIES = ["low", "medium", "high", "critical"]
SOURCES = ["1930 Cybercrime Helpline", "Bank Transfer Flag", "OSINT / News"]

OFFICERS = [
    Officer(officer_id="OFF-01", name="A. Kulkarni", badge_id="NDL-1041", role="nodal",
           status="Active Investigation", last_action="Reviewing escalation queue"),
    Officer(officer_id="OFF-02", name="V. Sharma", badge_id="IO-2207", role="io",
           status="Active Investigation", assigned_case_id="CYB-1001", last_action="Tracing layering chain CYB-1001"),
    Officer(officer_id="OFF-03", name="N. Iyer", badge_id="AN-3390", role="analyst",
           status="Active Investigation", last_action="Monitoring live transfer feed"),
    Officer(officer_id="OFF-04", name="R. Fernandes", badge_id="IO-2214", role="io",
           status="Cold Case", assigned_case_id="CYB-1002", last_action="Awaiting bank KYC response"),
    Officer(officer_id="OFF-05", name="S. Bano", badge_id="AN-3391", role="analyst",
           status="Available", last_action="Signed on"),
]


def seed_cases() -> dict[str, CyberCase]:
    now = datetime.now(timezone.utc)
    cases = {
        "CYB-1001": CyberCase(
            case_id="CYB-1001", title="Layered mule-network transfer — ₹8.4L",
            crime_type="Mule Network", severity="critical", status="Active Investigation",
            assigned_officer_id="OFF-02", source_account="AC-VICTIM-4471",
            layering_path=["AC-VICTIM-4471", "AC-MULE-2291", "AC-MULE-5567", "CRYPTO-WALLET-9F3A"],
            amount=840_000, created_at=now - timedelta(hours=3),
            history=[
                CaseEvent(actor="system", action="Transaction flagged by rule engine — destination is a known mule account.", ts=now - timedelta(hours=3)),
                CaseEvent(actor="system", action="Case CYB-1001 opened, assigned to V. Sharma (IO-2207).", ts=now - timedelta(hours=3)),
                CaseEvent(actor="human", action="V. Sharma began tracing the layering chain.", ts=now - timedelta(hours=2, minutes=40)),
            ],
        ),
        "CYB-1002": CyberCase(
            case_id="CYB-1002", title="Phishing-led account takeover — ₹2.1L",
            crime_type="Phishing", severity="high", status="Cold Case",
            assigned_officer_id="OFF-04", source_account="AC-VICTIM-8820",
            layering_path=["AC-VICTIM-8820", "AC-MULE-8834", "AC-CASHOUT-1187"],
            amount=210_000, created_at=now - timedelta(days=2),
            history=[
                CaseEvent(actor="system", action="Case CYB-1002 opened, assigned to R. Fernandes (IO-2214).", ts=now - timedelta(days=2)),
                CaseEvent(actor="human", action="Requested KYC records from beneficiary bank — awaiting response.", ts=now - timedelta(days=1, hours=6)),
            ],
        ),
    }
    return cases


def seed_geo_incidents(n: int = 60, seed: int = 11) -> list[GeoIncident]:
    rng = random.Random(seed)
    now = datetime.now(timezone.utc)
    incidents = []
    for i in range(n):
        city, state, lat, lng = rng.choice(CITIES)
        # small jitter so points don't all stack on the exact city centroid
        jlat, jlng = lat + rng.uniform(-0.15, 0.15), lng + rng.uniform(-0.15, 0.15)
        crime = rng.choice(CRIME_TYPES)
        severity = rng.choices(SEVERITIES, weights=[35, 35, 22, 8])[0]
        source = rng.choice(SOURCES)
        incidents.append(GeoIncident(
            incident_id=f"GEO-{i+1:04d}", lat=round(jlat, 4), lng=round(jlng, 4), city=city, state=state,
            crime_type=crime, severity=severity, source=source,
            reported_at=now - timedelta(hours=rng.uniform(0, 24 * 30)),
            description=f"{crime} incident reported via {source} in {city}, {state}.",
        ))
    return incidents


def seed_graph(case_id: str) -> tuple[list[GraphEntity], list[GraphEdge]]:
    """Entity-relationship graph for a case — suspect/financial/spatial nodes,
    same 'evidence, not a verdict' framing as the compliance module's graph:
    confidence scores are shown, never asserted as fact."""
    nodes = [
        GraphEntity(id="P-9821", type="phone_number", label="+91 98xxxx9821", confidence=0.82,
                   details={"carrier": "Regional Telecom", "registered_name": "Unverified"}),
        GraphEntity(id="SM-mulevault21", type="social_media_handle", label="@mulevault21", confidence=0.61,
                   details={"platform": "Telegram", "activity": "Recruitment posts for 'easy money' account rentals"}),
        GraphEntity(id="IMEI-3F7A9C", type="imei", label="IMEI 3F7A...9C", confidence=0.74,
                   details={"device_model": "Unregistered Android handset"}),
        GraphEntity(id="AC-MULE-2291", type="bank_account", label="AC-MULE-2291", confidence=0.95,
                   details={"bank": "Regional Cooperative Bank", "status": "Flagged mule account"}),
        GraphEntity(id="UPI-mule2291@upi", type="upi_id", label="mule2291@upi", confidence=0.90,
                   details={"linked_account": "AC-MULE-2291"}),
        GraphEntity(id="CRYPTO-9F3A", type="crypto_wallet", label="0x9F3A...b21c", confidence=0.55,
                   details={"chain": "synthetic-demo-chain", "exchange_flag": "Unhosted wallet"}),
        GraphEntity(id="IP-103.22.x", type="ip_address", label="103.22.xx.xx", confidence=0.68,
                   details={"geo": "Shared VPN exit node"}),
        GraphEntity(id="CT-JMT-04", type="cell_tower", label="Tower JMT-04", confidence=0.71,
                   details={"location": "Jamtara cluster"}),
        GraphEntity(id="FIR-2026-0447", type="fir_report", label="FIR 2026/0447", confidence=1.0,
                   details={"station": "Cyber Cell HQ", "filed_by": "Victim complaint via 1930 helpline"}),
    ]
    edges = [
        GraphEdge(src="P-9821", tgt="SM-mulevault21", relationship_type="linked_to_handle", confidence=0.6),
        GraphEdge(src="P-9821", tgt="IMEI-3F7A9C", relationship_type="used_on_device", confidence=0.7),
        GraphEdge(src="IMEI-3F7A9C", tgt="CT-JMT-04", relationship_type="last_seen_near", confidence=0.65),
        GraphEdge(src="SM-mulevault21", tgt="AC-MULE-2291", relationship_type="advertised_account", confidence=0.58),
        GraphEdge(src="AC-MULE-2291", tgt="UPI-mule2291@upi", relationship_type="linked_upi", confidence=0.92),
        GraphEdge(src="AC-MULE-2291", tgt="CRYPTO-9F3A", relationship_type="funds_forwarded_to", confidence=0.55),
        GraphEdge(src="AC-MULE-2291", tgt="IP-103.22.x", relationship_type="accessed_from", confidence=0.6),
        GraphEdge(src="FIR-2026-0447", tgt="AC-MULE-2291", relationship_type="named_in_report", confidence=1.0),
    ]
    return nodes, edges
