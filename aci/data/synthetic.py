"""
Synthetic data strategy (§19).

Two producers:
  1. seed_world()      -> the hand-crafted demo world (TX-84721 and friends).
  2. generate_bulk(n)  -> a labelled population for the evaluation harness.

`scenario_type` is ground truth for evaluation only and is NEVER handed to an
agent during inference.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta

from aci.models import Customer, Document, Entity, Relationship, Transaction

# ── Hand-crafted demo world ────────────────────────────────────────────────
CUSTOMERS = {
    "C-1001": Customer(customer_id="C-1001", name="Meridian Textiles Pvt Ltd", country="India",
                       industry="Textile manufacturing & export", onboarded="2019-03-11", entity_id="E-A"),
    "C-1002": Customer(customer_id="C-1002", name="Sundar Logistics LLP", country="India",
                       industry="Freight & logistics", onboarded="2021-07-02", entity_id="E-D"),
    "C-1003": Customer(customer_id="C-1003", name="Kaveri Exports Pvt Ltd", country="India",
                       industry="Agri commodities", risk_profile="elevated", onboarded="2022-11-19", entity_id="E-K"),
    # A clean Risk-Based Approach demo: nothing about THIS transaction is
    # anomalous on its own (amount near baseline, established counterparty,
    # no shared directors, well-documented) — it lands MEDIUM/HIGH only
    # because of the customer's own persistent risk rating (FATF R.1), making
    # the customer_risk dimension visibly the deciding factor rather than one
    # contributor among several.
    "C-1004": Customer(customer_id="C-1004", name="Continental Bullion Traders Pvt Ltd", country="India",
                       industry="Precious metals & bullion trading", risk_profile="high",
                       onboarded="2020-06-15", entity_id="E-M"),
}

# Historical transactions drive DETERMINISTIC stats. Median of C-1001 = 7,700,000.
HISTORY: dict[str, list[dict]] = {
    "C-1001": [
        {"amount": 6_200_000, "dest": "India", "date": "2025-01-14"},
        {"amount": 7_100_000, "dest": "India", "date": "2025-02-03"},
        {"amount": 7_700_000, "dest": "India", "date": "2025-03-22"},
        {"amount": 5_900_000, "dest": "United Kingdom", "date": "2025-04-10"},
        {"amount": 8_400_000, "dest": "India", "date": "2025-05-06"},
        {"amount": 7_700_000, "dest": "India", "date": "2025-06-01"},
        {"amount": 9_050_000, "dest": "United Kingdom", "date": "2025-06-28"},
        {"amount": 7_700_000, "dest": "India", "date": "2025-07-15"},
        {"amount": 8_100_000, "dest": "India", "date": "2025-07-29"},
        {"amount": 6_800_000, "dest": "India", "date": "2025-08-04"},
    ],
    "C-1002": [
        {"amount": 1_200_000, "dest": "Singapore", "date": "2025-05-02"},
        {"amount": 1_450_000, "dest": "Singapore", "date": "2025-06-11"},
        {"amount": 1_300_000, "dest": "Singapore", "date": "2025-07-09"},
        {"amount": 1_600_000, "dest": "Singapore", "date": "2025-08-01"},
    ],
    "C-1003": [
        {"amount": 980_000, "dest": "UAE", "date": "2025-07-20"},
        {"amount": 990_000, "dest": "UAE", "date": "2025-07-23"},
        {"amount": 985_000, "dest": "UAE", "date": "2025-07-27"},
        {"amount": 995_000, "dest": "UAE", "date": "2025-08-02"},
    ],
    "C-1004": [
        # Deliberately kept outside the trailing-30-day window from the demo
        # transaction (2025-08-10) so the velocity signal never fires here —
        # this customer's baseline behaviour is genuinely unremarkable.
        {"amount": 2_950_000, "dest": "Singapore", "date": "2025-02-10"},
        {"amount": 3_050_000, "dest": "Singapore", "date": "2025-03-15"},
        {"amount": 3_100_000, "dest": "Singapore", "date": "2025-04-20"},
        {"amount": 2_980_000, "dest": "Singapore", "date": "2025-05-25"},
        {"amount": 3_050_000, "dest": "Singapore", "date": "2025-06-28"},
    ],
}

ENTITIES = {
    "E-A": Entity(entity_id="E-A", name="Meridian Textiles Pvt Ltd", entity_type="company",
                  country="India", registered="2019-03-11", directors=["P-X"]),
    "E-B": Entity(entity_id="E-B", name="Gulf Consulting Advisory FZE", entity_type="company",
                  country="UAE", registered="2025-04-02", directors=["P-X", "P-Y"]),
    "E-C": Entity(entity_id="E-C", name="Apex Nominee Holdings Pte Ltd", entity_type="company",
                  country="Singapore", registered="2023-09-15", directors=["P-Y"]),
    "E-D": Entity(entity_id="E-D", name="Sundar Logistics LLP", entity_type="company",
                  country="India", registered="2021-07-02", directors=["P-Z"]),
    "E-K": Entity(entity_id="E-K", name="Kaveri Exports Pvt Ltd", entity_type="company",
                  country="India", registered="2022-11-19", directors=["P-Z"]),
    "E-M": Entity(entity_id="E-M", name="Continental Bullion Traders Pvt Ltd", entity_type="company",
                  country="India", registered="2020-06-15", directors=["P-M"]),
    "E-N": Entity(entity_id="E-N", name="Straits Precious Metals Pte Ltd", entity_type="company",
                  country="Singapore", registered="2017-02-10", directors=["P-N"]),
    "P-X": Entity(entity_id="P-X", name="Rajiv Menon", entity_type="individual", country="India"),
    "P-Y": Entity(entity_id="P-Y", name="Lian Tan", entity_type="individual", country="Singapore"),
    "P-Z": Entity(entity_id="P-Z", name="Ananya Krishnan", entity_type="individual", country="India"),
    "P-M": Entity(entity_id="P-M", name="Vikram Oberoi", entity_type="individual", country="India"),
    "P-N": Entity(entity_id="P-N", name="Wei Ling Goh", entity_type="individual", country="Singapore"),
}

RELATIONSHIPS = [
    Relationship(src="P-X", tgt="E-A", relationship_type="director_of", confidence=0.99, source="Corporate registry (synthetic)"),
    Relationship(src="P-X", tgt="E-B", relationship_type="director_of", confidence=0.86, source="Corporate registry (synthetic)"),
    Relationship(src="E-C", tgt="E-B", relationship_type="beneficial_owner_of", confidence=0.74, source="UBO filing (synthetic, unverified)"),
    Relationship(src="P-Y", tgt="E-C", relationship_type="director_of", confidence=0.95, source="Corporate registry (synthetic)"),
    # No shared directors on the C-1004 corridor — deliberately isolated so
    # entity_agent contributes NONE, keeping the RBA demo clean (see C-1004).
    Relationship(src="P-M", tgt="E-M", relationship_type="director_of", confidence=0.99, source="Corporate registry (synthetic)"),
    Relationship(src="P-N", tgt="E-N", relationship_type="director_of", confidence=0.97, source="Corporate registry (synthetic)"),
]

DOCUMENTS = {
    "TX-84721": Document(transaction_id="TX-84721", doc_type="invoice", narrative="General consulting services", amount=48_000_000),
    "TX-90233": Document(transaction_id="TX-90233", doc_type="invoice", narrative="Commodity handling split billing", amount=995_000),
    "TX-77310": Document(transaction_id="TX-77310", doc_type="invoice", narrative="Freight forwarding Q3 lane SG BOM itemised", amount=1_600_000),
    "TX-31204": Document(transaction_id="TX-31204", doc_type="invoice", narrative="Bullion consignment settlement per supply contract, itemised assay certificate attached", amount=3_100_000),
}

TRANSACTIONS = {
    "TX-84721": Transaction(transaction_id="TX-84721", customer_id="C-1001", amount=48_000_000,
                            source_country="India", destination_country="UAE", ultimate_destination="Singapore",
                            beneficiary_id="E-B", beneficiary_registered="2025-04-02",
                            timestamp="2025-08-11T09:41:00+05:30", purpose="Consulting services",
                            route=["India", "UAE", "Singapore"], scenario_type="multi_signal"),
    "TX-90233": Transaction(transaction_id="TX-90233", customer_id="C-1003", amount=995_000,
                            source_country="India", destination_country="UAE", ultimate_destination="UAE",
                            beneficiary_id="E-B", beneficiary_registered="2025-04-02",
                            timestamp="2025-08-02T16:05:00+05:30", purpose="Commodity handling",
                            route=["India", "UAE"], scenario_type="structuring"),
    "TX-77310": Transaction(transaction_id="TX-77310", customer_id="C-1002", amount=1_600_000,
                            source_country="India", destination_country="Singapore", ultimate_destination="Singapore",
                            beneficiary_id="E-C", beneficiary_registered="2023-09-15",
                            timestamp="2025-08-01T11:12:00+05:30", purpose="Freight forwarding",
                            route=["India", "Singapore"], scenario_type="normal"),
    "TX-31204": Transaction(transaction_id="TX-31204", customer_id="C-1004", amount=3_100_000,
                            source_country="India", destination_country="Singapore", ultimate_destination="Singapore",
                            beneficiary_id="E-N", beneficiary_registered="2017-02-10",
                            timestamp="2025-08-10T14:20:00+05:30", purpose="Bullion trade settlement",
                            route=["India", "Singapore"], scenario_type="customer_risk_only"),
}


class World:
    """A resolvable bundle of everything an agent might need to look up."""
    def __init__(self, customers, history, entities, relationships, documents, transactions):
        self.customers = customers
        self.history = history
        self.entities = entities
        # Normalised to a list regardless of how the producer built it:
        # seed_world() passes a list while generate_bulk() accumulates a dict,
        # and consumers previously had to isinstance-check every access.
        self.relationships = list(relationships.values()) if isinstance(relationships, dict) else list(relationships)
        self.documents = documents
        self.transactions = transactions

    def customer(self, cid): return self.customers[cid]
    def entity(self, eid): return self.entities.get(eid)
    def doc(self, tid): return self.documents.get(tid)
    def hist(self, cid): return self.history.get(cid, [])


def seed_world() -> World:
    """Returns a fresh, independent copy of the demo world every call. The
    module-level CUSTOMERS/HISTORY/ENTITIES/... dicts are the canonical demo
    data — mutating what seed_world() returns (as tests and the API's request
    handling both legitimately do) must never leak into the next caller."""
    return World(
        dict(CUSTOMERS), {k: list(v) for k, v in HISTORY.items()}, dict(ENTITIES),
        list(RELATIONSHIPS), dict(DOCUMENTS), dict(TRANSACTIONS),
    )


# ── Bulk generator for evaluation (§19, §28) ────────────────────────────────
# Every generated customer gets its OWN sender-side entity + director, linked
# via Customer.entity_id — required for the Entity Intelligence agent to ever
# resolve a sender, and for a common-director finding to be detectable at all.
def generate_bulk(n_normal: int = 800, n_anomalous: int = 200, seed: int = 7) -> World:
    """Produce a labelled population: normal customers plus injected suspicious
    scenarios, so precision/recall can be measured against ground truth. Ground
    truth (`scenario_type`) is for THIS function's caller only — never passed
    to an agent during inference (§19)."""
    rng = random.Random(seed)
    customers, history, entities, relationships, documents, transactions = {}, {}, {}, {}, {}, {}
    base = datetime(2025, 8, 1)

    # ~5% of customers carry an elevated/high persistent risk rating,
    # independent of scenario_type — a Risk-Based Approach means the customer
    # dimension is orthogonal to any single transaction's own behaviour, so
    # this must not correlate with which scenario a customer was assigned.
    def sample_risk_profile() -> str:
        return rng.choices(["standard", "elevated", "high"], weights=[95, 3, 2])[0]

    def add_customer(i: int, baseline: int, n_hist: int = 7, spacing_days: int = 30):
        cid = f"G-{1000 + i}"
        sender_eid = f"GS-{i}"
        director_id = f"GP-{i}"
        entities[director_id] = Entity(entity_id=director_id, name=f"Director {i}",
                                       entity_type="individual", country="India")
        entities[sender_eid] = Entity(entity_id=sender_eid, name=f"SenderCo {i}", entity_type="company",
                                      country="India", registered="2020-01-01", directors=[director_id])
        relationships[f"r{i}-dir"] = Relationship(src=director_id, tgt=sender_eid,
                                                   relationship_type="director_of", confidence=0.95,
                                                   source="synthetic")
        customers[cid] = Customer(customer_id=cid, name=f"SynthCorp {i}", country="India",
                                  industry="general", onboarded="2021-01-01", entity_id=sender_eid,
                                  risk_profile=sample_risk_profile())
        history[cid] = [{"amount": int(baseline * rng.uniform(0.75, 1.25)),
                         "dest": "India", "date": (base - timedelta(days=spacing_days * k)).strftime("%Y-%m-%d")}
                        for k in range(1, n_hist + 1)]
        return cid, sender_eid, director_id, baseline

    idx = 0
    # Normal population — includes realistic noise: seasonal spikes, occasional
    # first-time counterparties that never cross the anomaly thresholds. A
    # population with none of this makes any detector look artificially perfect.
    for _ in range(n_normal):
        baseline = rng.choice([2_000_000, 5_000_000, 8_000_000])
        cid, sender_eid, _, baseline = add_customer(idx, baseline)
        eid = f"GE-{idx}"
        # ~15% of "normal" beneficiaries are recently onboarded but otherwise
        # unremarkable — a legitimate new counterparty, not an anomaly by itself.
        registered = "2025-05-01" if rng.random() < 0.15 else "2022-01-01"
        entities[eid] = Entity(entity_id=eid, name=f"Beneficiary {idx}", entity_type="company",
                               country="Singapore", registered=registered)
        tid = f"GT-{idx}"
        # occasional legitimate spike, capped below the MEDIUM ratio threshold (1.8x)
        spike = rng.uniform(1.3, 1.7) if rng.random() < 0.08 else rng.uniform(0.8, 1.2)
        transactions[tid] = Transaction(transaction_id=tid, customer_id=cid,
                                         amount=int(baseline * spike),
                                         source_country="India", destination_country="Singapore",
                                         ultimate_destination="Singapore", beneficiary_id=eid,
                                         beneficiary_registered=registered,
                                         timestamp="2025-08-05T10:00:00+05:30", purpose="trade settlement",
                                         route=["India", "Singapore"], scenario_type="normal")
        documents[tid] = Document(transaction_id=tid, doc_type="invoice",
                                  narrative="itemised trade settlement invoice with line items", amount=int(baseline * spike))
        idx += 1

    # Anomalous population — one injected pattern each, covering all eight
    # blueprint patterns (§19). Amounts/timings are randomised within a band
    # so ground truth is a risk indicator, not a guaranteed detection.
    patterns = ["amount_anomaly", "new_counterparty", "relationship_anomaly", "structuring",
                "documentation_anomaly", "rapid_movement", "missing_documentation", "multi_signal"]
    for k in range(n_anomalous):
        pattern = patterns[k % len(patterns)]
        baseline = 5_000_000
        cid, sender_eid, director_id, baseline = add_customer(idx, baseline)
        eid = f"GE-{idx}"
        registered = "2022-01-01"
        amount = baseline
        purpose = "trade settlement"
        route = ["India", "Singapore"]
        narrative = "itemised trade settlement invoice with line items"
        skip_doc = False

        if pattern == "amount_anomaly":
            amount = int(baseline * rng.uniform(3.2, 8.0))
        elif pattern == "new_counterparty":
            registered = "2025-06-01"
        elif pattern == "relationship_anomaly":
            # common director between sender-side and beneficiary
            registered = "2025-06-01"
            relationships[f"r{idx}-ubo"] = Relationship(src=director_id, tgt=eid,
                                                         relationship_type="director_of", confidence=0.85,
                                                         source="synthetic")
        elif pattern == "structuring":
            history[cid] = [{"amount": 950_000 + rng.randint(0, 40_000), "dest": "UAE",
                             "date": (base - timedelta(days=3 * j)).strftime("%Y-%m-%d")} for j in range(5)]
            amount = 980_000
            route = ["India", "UAE"]
        elif pattern == "documentation_anomaly":
            amount = int(baseline * 1.1)
            narrative = "services"  # too generic for the value
        elif pattern == "rapid_movement":
            # dense trailing-30-day cadence — velocity signal
            history[cid] = [{"amount": int(baseline * rng.uniform(0.8, 1.2)), "dest": "India",
                             "date": (base - timedelta(days=2 * j)).strftime("%Y-%m-%d")} for j in range(10)]
            route = ["India", "UAE", "Singapore"]
        elif pattern == "missing_documentation":
            skip_doc = True
        elif pattern == "multi_signal":
            amount = int(baseline * rng.uniform(4.0, 7.0))
            registered = "2025-06-01"
            route = ["India", "UAE", "Singapore"]
            relationships[f"r{idx}-ubo"] = Relationship(src=director_id, tgt=eid,
                                                         relationship_type="director_of", confidence=0.85,
                                                         source="synthetic")

        entities.setdefault(eid, Entity(entity_id=eid, name=f"Beneficiary {idx}", entity_type="company",
                                        country=route[-1] if route[-1] != "India" else "UAE",
                                        registered=registered))
        tid = f"GT-{idx}"
        transactions[tid] = Transaction(transaction_id=tid, customer_id=cid, amount=amount,
                                        source_country="India", destination_country=route[1],
                                        ultimate_destination=route[-1], beneficiary_id=eid,
                                        beneficiary_registered=registered,
                                        timestamp="2025-08-05T10:00:00+05:30", purpose=purpose,
                                        route=route, scenario_type=pattern)
        if not skip_doc:
            documents[tid] = Document(transaction_id=tid, doc_type="invoice", narrative=narrative, amount=amount)
        idx += 1

    return World(customers, history, entities, relationships, documents, transactions)
