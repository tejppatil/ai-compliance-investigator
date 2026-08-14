"""
Cyber Crime module tests.

The rule engine is the part that must be provably correct — a flag has to
trace to a named threshold, exactly like the compliance module's
deterministic signals. These tests drive aci/cybercrime/rules.py directly
with constructed transactions rather than waiting on the live simulator, so
they're fast and deterministic.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from aci.cybercrime import rules
from aci.cybercrime.models import LiveTransaction
from aci.cybercrime.simulator import TransactionSimulator
from aci.cybercrime.store import CyberStore


def _txn(**over) -> LiveTransaction:
    base = dict(tx_id="LTX-TEST", source_account="AC-1000", destination_account="AC-2000",
                amount=10_000, channel="UPI", city="Mumbai", lat=19.07, lng=72.87, hop_index=0)
    base.update(over)
    return LiveTransaction(**base)


# ── rule engine ──────────────────────────────────────────────────────────

def test_clean_transaction_is_not_flagged():
    flagged, reasons, score = rules.evaluate(_txn(), [])
    assert flagged is False
    assert reasons == []
    assert score == 0


def test_known_mule_destination_is_flagged():
    mule = sorted(rules.MULE_ACCOUNT_BLACKLIST)[0]
    flagged, reasons, score = rules.evaluate(_txn(destination_account=mule), [])
    assert flagged is True
    assert any(mule in r for r in reasons)
    assert score >= 40


def test_layering_depth_is_flagged():
    flagged, reasons, _ = rules.evaluate(_txn(hop_index=2), [])
    assert flagged is True
    assert any("layering chain" in r for r in reasons)


def test_velocity_burst_is_flagged():
    now = datetime.now(timezone.utc)
    recent = [_txn(tx_id=f"LTX-{i}", ts=now - timedelta(seconds=10 * i)) for i in range(1, 3)]
    flagged, reasons, _ = rules.evaluate(_txn(), recent)
    assert flagged is True
    assert any("transfers from" in r for r in reasons)


def test_high_risk_location_is_flagged():
    city = sorted(rules.HIGH_RISK_LOCATIONS)[0]
    flagged, reasons, _ = rules.evaluate(_txn(city=city), [])
    assert flagged is True
    assert any(city in r for r in reasons)


def test_risk_score_is_capped_at_100():
    """Several rules firing at once must not produce a nonsense >100 score."""
    mule = sorted(rules.MULE_ACCOUNT_BLACKLIST)[0]
    city = sorted(rules.HIGH_RISK_LOCATIONS)[0]
    now = datetime.now(timezone.utc)
    recent = [_txn(tx_id=f"LTX-{i}", ts=now - timedelta(seconds=5 * i)) for i in range(1, 4)]
    _, reasons, score = rules.evaluate(
        _txn(destination_account=mule, city=city, hop_index=3, amount=5_000_000), recent)
    assert len(reasons) == 5  # every rule fired
    assert score == 100


def test_every_flag_carries_a_reason():
    """A flag with no stated reason would be exactly the black box this
    project refuses to ship."""
    sim = TransactionSimulator(seed=3)
    for _ in range(200):
        txn = sim.tick()
        if txn.flagged:
            assert txn.flag_reasons, f"{txn.tx_id} flagged with no reason"
            assert txn.risk_score > 0


# ── simulator ────────────────────────────────────────────────────────────

def test_simulator_is_deterministic_for_a_seed():
    a = [t.tx_id + t.destination_account for t in (TransactionSimulator(seed=42).tick() for _ in range(20))]
    b = [t.tx_id + t.destination_account for t in (TransactionSimulator(seed=42).tick() for _ in range(20))]
    assert a == b


def test_simulator_produces_both_clean_and_flagged_traffic():
    """A feed that flags everything (or nothing) would make the whole
    dashboard meaningless."""
    sim = TransactionSimulator(seed=7)
    txns = [sim.tick() for _ in range(300)]
    flagged = [t for t in txns if t.flagged]
    assert 0 < len(flagged) < len(txns)


def test_simulator_advances_layering_chains_hop_by_hop():
    """The IO view's whole premise is money moving one hop at a time, so a
    chain must not complete within a single tick."""
    sim = TransactionSimulator(seed=5)
    txns = [sim.tick() for _ in range(400)]
    assert any(t.hop_index >= 2 for t in txns), "no multi-hop layering ever generated"


# ── store actions ────────────────────────────────────────────────────────

def test_escalation_updates_case_and_officer():
    store = CyberStore()
    case = store.escalate_case("CYB-1001", "V. Sharma", "confirmed layering")
    assert case.escalation_level == 1
    assert case.status == "Escalated to Nodal"
    assert "escalated CYB-1001" in case.history[-1].action
    assert store.officers[case.assigned_officer_id].status == "Escalated to Nodal"


def test_transfer_reassigns_and_frees_the_previous_officer():
    store = CyberStore()
    original = store.cases["CYB-1001"].assigned_officer_id
    case = store.transfer_case("CYB-1001", "OFF-05", "A. Kulkarni")
    assert case.assigned_officer_id == "OFF-05"
    assert store.officers["OFF-05"].assigned_case_id == "CYB-1001"
    assert store.officers[original].assigned_case_id is None


def test_freeze_hop_records_the_officer_who_did_it():
    """Attribution is the whole accountability model here — a freeze with no
    named officer would be untraceable."""
    store = CyberStore()
    case = store.freeze_case_hop("CYB-1001", 1, "V. Sharma")
    assert 1 in case.frozen_hops
    assert case.history[-1].actor == "V. Sharma"
    assert "HOLDING FREEZE" in case.history[-1].action


def test_freeze_hop_is_idempotent():
    store = CyberStore()
    store.freeze_case_hop("CYB-1001", 1, "V. Sharma")
    case = store.freeze_case_hop("CYB-1001", 1, "V. Sharma")
    assert case.frozen_hops.count(1) == 1


def test_freeze_hop_rejects_an_out_of_range_hop():
    store = CyberStore()
    with pytest.raises(ValueError):
        store.freeze_case_hop("CYB-1001", 99, "V. Sharma")


def test_unknown_case_raises():
    store = CyberStore()
    with pytest.raises(KeyError):
        store.escalate_case("CYB-NOPE", "V. Sharma")


# ── API surface ──────────────────────────────────────────────────────────

def test_cyber_endpoints_respond():
    from fastapi.testclient import TestClient
    from aci.api.app import app

    client = TestClient(app)
    assert len(client.get("/api/cyber/officers").json()) >= 3
    assert len(client.get("/api/cyber/cases").json()) >= 1

    graph = client.get("/api/cyber/graph/CYB-1001").json()
    assert graph["nodes"] and graph["edges"]
    # Every edge must connect two nodes that actually exist in the payload.
    ids = {n["id"] for n in graph["nodes"]}
    for e in graph["edges"]:
        assert e["src"] in ids and e["tgt"] in ids

    assert client.get("/api/cyber/graph/CYB-NOPE").status_code == 404


def test_geo_incident_filters_narrow_results():
    from fastapi.testclient import TestClient
    from aci.api.app import app

    client = TestClient(app)
    everything = client.get("/api/cyber/geo-incidents").json()
    high = client.get("/api/cyber/geo-incidents?severity=high").json()
    phishing = client.get("/api/cyber/geo-incidents?crime_type=Phishing").json()

    assert len(everything) > 0
    assert all(i["severity"] == "high" for i in high)
    assert all(i["crime_type"] == "Phishing" for i in phishing)
    assert len(high) < len(everything)
