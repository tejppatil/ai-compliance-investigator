"""
Detection rules catalogue — a single, inspectable reference for every
deterministic rule this system actually runs, surfaced via GET /api/rules.

Every trigger description below states the REAL threshold from aci/config.py,
not a paraphrase that could drift from the code (`f"{config.X}"` inline is
kept deliberately live). This is a catalogue of what's already implemented in
aci/agents/*.py — writing a new rule here does nothing; the logic itself lives
in the agent that owns it. This file only describes it in one place instead of
leaving a reader to reconstruct the rule set by reading four separate agents.
"""
from __future__ import annotations

from aci import config
from aci.agents import document_agent


def catalog() -> list[dict]:
    return [
        {"key": "amount_anomaly", "agent": "transaction_intelligence", "category": "behavioural",
         "file": "aci/agents/transaction_agent.py",
         "trigger": f"Transaction amount ÷ customer's own historical median ≥ {config.AMOUNT_RATIO_HIGH}x → HIGH; ≥ {config.AMOUNT_RATIO_MEDIUM}x → MEDIUM."},
        {"key": "new_counterparty", "agent": "transaction_intelligence", "category": "behavioural",
         "file": "aci/agents/transaction_agent.py",
         "trigger": f"Beneficiary was registered ≤ {config.NEW_COUNTERPARTY_MONTHS} months before this transaction → MEDIUM."},
        {"key": "route_change", "agent": "transaction_intelligence", "category": "behavioural",
         "file": "aci/agents/transaction_agent.py",
         "trigger": "Destination country never seen in this customer's transaction history → MEDIUM."},
        {"key": "structuring", "agent": "transaction_intelligence", "category": "behavioural",
         "file": "aci/agents/transaction_agent.py",
         "trigger": (f"≥3 recent transfers land in [{config.STRUCTURING_BAND}×, 1.0×) of the "
                    f"INR {config.REPORTING_THRESHOLD:,} reporting threshold → HIGH.")},
        {"key": "velocity", "agent": "transaction_intelligence", "category": "behavioural",
         "file": "aci/agents/transaction_agent.py",
         "trigger": f"Trailing-30-day transaction count ≥ {config.VELOCITY_MULTIPLIER}x the customer's per-week baseline → MEDIUM."},
        {"key": "rapid_movement", "agent": "transaction_intelligence", "category": "behavioural",
         "file": "aci/agents/transaction_agent.py",
         "trigger": f"Velocity ≥ {config.VELOCITY_MULTIPLIER * 1.5}x baseline AND the route crosses ≥3 jurisdictions (layering) → HIGH."},
        {"key": "common_director", "agent": "entity_intelligence", "category": "relationship",
         "file": "aci/agents/entity_agent.py",
         "trigger": "Same individual is recorded as director of both the sender-side and beneficiary-side entity → MEDIUM. Never asserted as wrongdoing — additional due diligence recommended."},
        {"key": "ownership_chain", "agent": "entity_intelligence", "category": "relationship",
         "file": "aci/agents/entity_agent.py",
         "trigger": "Beneficiary entity has a recorded beneficial owner in a further jurisdiction → MEDIUM. Ownership is not independently verified by this system."},
        {"key": "generic_narrative", "agent": "document_analysis", "category": "documentation",
         "file": "aci/agents/document_agent.py",
         "trigger": f"Invoice narrative ≤ {document_agent.GENERIC_NARRATIVE_WORD_LIMIT} words on a transaction ≥ INR 5,000,000 → MEDIUM."},
        {"key": "amount_mismatch", "agent": "document_analysis", "category": "documentation",
         "file": "aci/agents/document_agent.py",
         "trigger": (f"Invoice amount vs. transaction amount deviates >{document_agent.AMOUNT_MISMATCH_THRESHOLD:.0%} "
                    f"→ MEDIUM, >{document_agent.AMOUNT_MISMATCH_HIGH:.0%} → HIGH.")},
        {"key": "missing_documentation", "agent": "document_analysis", "category": "documentation",
         "file": "aci/agents/document_agent.py",
         "trigger": "No document attached to the transaction at all → HIGH."},
        {"key": "customer_risk_rating", "agent": "risk_engine", "category": "customer",
         "file": "aci/agents/risk_agent.py",
         "trigger": "Customer's persistent risk_profile: standard → LOW, elevated → MEDIUM, high → HIGH — independent of this transaction's own behaviour (FATF R.1)."},
        {"key": "jurisdictional_complexity", "agent": "risk_engine", "category": "geography",
         "file": "aci/agents/risk_agent.py",
         "trigger": "Payment route crosses 2 jurisdictions → LOW, ≥3 → MEDIUM."},
        {"key": "kyc_name_mismatch", "agent": "kyc_completeness", "category": "kyc",
         "file": "aci/agents/kyc_agent.py",
         "trigger": "Customer's registered name materially differs from its linked corporate entity's name."},
        {"key": "kyc_missing_ownership", "agent": "kyc_completeness", "category": "kyc",
         "file": "aci/agents/kyc_agent.py",
         "trigger": "Linked entity has no registration date and/or no recorded director — beneficial-ownership data is incomplete."},
        {"key": "kyc_date_inconsistency", "agent": "kyc_completeness", "category": "kyc",
         "file": "aci/agents/kyc_agent.py",
         "trigger": "Entity's registration date falls after the customer's own onboarding date — a chronological impossibility worth flagging as a data-quality issue."},
    ]
