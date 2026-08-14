"""
SYNTHETIC sanctions / watchlist data — every entry below is FABRICATED.

No real sanctions list is embedded, scraped, or redistributed here. There is
no OFAC SDN, UN Consolidated, EU, or UK OFSI content in this file. Every
name, alias, date, programme, and list name is invented for this prototype,
in the same spirit as the synthetic customers in aci/data/synthetic.py.

The list NAMES themselves are deliberately fictional too ("Synthetic
Consolidated Designations List") rather than borrowing a real regulator's
list name, so a screenshot of this screen can never be mistaken for a real
screening result against a real list. See docs/PROVENANCE.md.

**Any resemblance to a real person or organisation is coincidental and
unintended.** A production system would replace this module with a licensed
feed (and would need list versioning, delta updates, and a documented
refresh cadence — none of which this prototype claims to do).
"""
from __future__ import annotations

# Fictional list identifiers. Not real regulators, not real programmes.
LIST_SCDL = "Synthetic Consolidated Designations List (SCDL)"
LIST_SPEP = "Synthetic PEP & Adverse-Media Register (SPEP)"

# `aliases` model the real-world problem of transliteration and trade names —
# screening only the primary name misses a large share of true matches.
WATCHLIST: list[dict] = [
    {
        "entry_id": "SCDL-0001",
        "name": "Zarnex Petrochemical Trading FZCO",
        "aliases": ["Zarnex Petrochem FZCO", "Zarnex Trading Free Zone Company"],
        "entity_type": "company",
        "country": "UAE",
        "list": LIST_SCDL,
        "programme": "SYNTHETIC-PROGRAMME-A",
        "designated_on": "2024-03-18",
        "reason": "Fabricated designation for prototype demonstration — trade-based value transfer.",
    },
    {
        "entry_id": "SCDL-0002",
        "name": "Orlov Maritime Logistics OOO",
        "aliases": ["Orlov Maritime", "OML Shipping"],
        "entity_type": "company",
        "country": "Synthetica",
        "list": LIST_SCDL,
        "programme": "SYNTHETIC-PROGRAMME-B",
        "designated_on": "2023-11-02",
        "reason": "Fabricated designation for prototype demonstration — shipping network.",
    },
    {
        "entry_id": "SCDL-0003",
        "name": "Halvorsen Precious Metals AG",
        "aliases": ["Halvorsen Metals"],
        "entity_type": "company",
        "country": "Synthetica",
        "list": LIST_SCDL,
        "programme": "SYNTHETIC-PROGRAMME-A",
        "designated_on": "2025-01-27",
        "reason": "Fabricated designation for prototype demonstration — bullion movement.",
    },
    {
        "entry_id": "SCDL-0004",
        "name": "Dariusz Wolański",
        "aliases": ["Dariusz Wolanski", "D. Wolanski"],  # deliberate diacritic + short-form variants
        "entity_type": "individual",
        "country": "Synthetica",
        "list": LIST_SCDL,
        "programme": "SYNTHETIC-PROGRAMME-B",
        "designated_on": "2024-07-09",
        "reason": "Fabricated designation for prototype demonstration — control of designated entities.",
    },
    {
        "entry_id": "SPEP-0011",
        "name": "Marisol Ventura-Reyes",
        "aliases": ["M. Ventura Reyes", "Marisol Ventura"],
        "entity_type": "individual",
        "country": "Synthetica",
        "list": LIST_SPEP,
        "programme": "SYNTHETIC-PEP",
        "designated_on": "2022-05-14",
        "reason": "Fabricated politically-exposed-person record for prototype demonstration.",
    },
    {
        "entry_id": "SPEP-0012",
        "name": "Kwabena Osei-Bonsu",
        "aliases": ["K. Osei Bonsu"],
        "entity_type": "individual",
        "country": "Synthetica",
        "list": LIST_SPEP,
        "programme": "SYNTHETIC-PEP",
        "designated_on": "2023-02-28",
        "reason": "Fabricated politically-exposed-person record for prototype demonstration.",
    },
]


def all_entries() -> list[dict]:
    return WATCHLIST


def list_names() -> list[str]:
    return sorted({e["list"] for e in WATCHLIST})
