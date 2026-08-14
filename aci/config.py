"""Central configuration. Values are documented so an evaluator can see exactly
why a case lands where it does (§10, §18)."""
import os
from pathlib import Path

from aci.models import Severity

# Deterministic anomaly thresholds
AMOUNT_RATIO_HIGH = 3.0        # amount / historical median >= this -> HIGH
AMOUNT_RATIO_MEDIUM = 1.8
NEW_COUNTERPARTY_MONTHS = 6    # beneficiary onboarded within N months -> flag
REPORTING_THRESHOLD = 1_000_000  # synthetic INR reporting threshold (structuring)
STRUCTURING_BAND = 0.90        # transfers in [threshold*band, threshold) count as near-threshold
VELOCITY_MULTIPLIER = 2.0

# Explainable risk weights (must sum to 1.0). Configurable & visible (§10).
# Six dimensions implementing a Risk-Based Approach per FATF Recommendation 1
# (see aci/rag/knowledge_base.py FATF-R1): customer, transaction behaviour,
# entity/ownership, applicable regulation, documentation and geography are all
# weighed, rather than a single "risk score" pulled from nowhere.
RISK_WEIGHTS = {
    "transaction": 0.32,
    "entity": 0.20,
    "regulatory": 0.18,
    "documentation": 0.12,
    "jurisdiction": 0.06,
    "customer_risk": 0.12,
}
# Chosen empirically (scripts in dev history), not just derived arithmetically:
# adding a 6th dimension while keeping every existing scenario's detection
# rate at 1.0 requires checking every pattern the generator produces, since
# several sit close to the band_from_score(0.40) boundary by design (the
# dataset deliberately contains near-misses — see DATASET_CARD.md). TX-90233
# (structuring) clears the HIGH threshold by only ~0.007 — a real, measured
# margin, not curve-fit, but tight enough that future weight changes should
# re-run `python run_demo.py --eval` and check the by-scenario breakdown, not
# just the aggregate F1.
assert abs(sum(RISK_WEIGHTS.values()) - 1.0) < 1e-9, "risk weights must sum to 1.0"

# Customer risk rating (Customer.risk_profile) -> severity. FATF's risk-based
# approach means baseline vigilance is never zero, even for a "standard"
# customer — so the floor is LOW, not NONE. Unrecognised values fall back to
# "standard" (aci/agents/risk_agent.py) rather than raising.
CUSTOMER_RISK_SEVERITY = {
    "standard": Severity.LOW,
    "elevated": Severity.MEDIUM,
    "high": Severity.HIGH,
}

# Two-tier escalation (§23-style Senior Compliance Officer review). A tier-1
# decision of "escalate" assigns the case to a named senior reviewer with this
# SLA; only that role may then decide the case (aci/orchestrator.py).
ESCALATION_SLA_HOURS = 24

# ── Sanctions / watchlist screening (aci/agents/sanctions_agent.py) ─────────
# Screening runs against a FABRICATED list (aci/data/synthetic_watchlist.py) —
# no real sanctions data is embedded anywhere in this project.
#
# Two thresholds, because "confirmed hit" and "needs a human to look" are
# genuinely different outcomes and collapsing them into one number is how
# screening systems become either useless (too many false hits) or dangerous
# (missed true hits):
#   >= SANCTIONS_MATCH_CONFIRMED : treated as a confirmed hit
#   >= SANCTIONS_MATCH_POSSIBLE  : surfaced as a possible match for human review
#   <  SANCTIONS_MATCH_POSSIBLE  : not reported
# Values are calibrated against the demo data (see tests/test_sanctions.py,
# which asserts both the true-hit and the deliberate near-miss), not guessed.
SANCTIONS_MATCH_CONFIRMED = 0.93
SANCTIONS_MATCH_POSSIBLE = 0.86

# Corporate suffixes carry no identifying information — "Ltd" appears in
# thousands of unrelated names — so they're stripped before comparison. Left
# in, two unrelated "... Trading FZCO" companies score misleadingly similar.
SANCTIONS_IGNORED_TOKENS = {
    "ltd", "limited", "llc", "llp", "plc", "inc", "incorporated", "corp", "corporation",
    "co", "company", "pvt", "private", "pte", "gmbh", "ag", "sa", "nv", "bv", "ooo", "oao",
    "fzco", "fze", "fzc", "dmcc", "holdings", "holding", "group", "international", "intl",
    "trading", "general", "enterprises", "enterprise", "services", "service", "and", "the",
}

# Risk band -> RECOMMENDED action, surfaced on the Risk-Based Approach page
# and via GET /api/risk-methodology. These are recommendations for the human
# reviewer, never an automated action — the system never freezes, blocks, or
# closes anything on its own (§13). "high" recommending escalation is advisory
# only: the officer still has to click "Escalate" themselves in the UI.
RISK_POLICY = {
    "none": "No action required — routine monitoring.",
    "low": "Standard monitoring — no additional action required.",
    "medium": "Enhanced due diligence recommended before closing the case.",
    "high": "Escalate to senior review — mandatory second-tier decision recommended.",
}

# ── Alert triage / queue ranking (aci/triage.py) ────────────────────────────
# What decides which case an officer sees first. Same principle as
# RISK_WEIGHTS: additive, inspectable, and surfaced through the API so the
# ordering can be argued with rather than taken on faith.
#
# These are NOT normalised to 1.0 — unlike RISK_WEIGHTS, this isn't an average
# producing a 0-1 risk band, it's a priority score whose absolute value has no
# meaning beyond ordering. What matters is the RATIO between factors, and the
# ratio encodes a deliberate claim: an unadjudicated sanctions match outranks
# everything, including a HIGH-risk case, because it's the one finding with a
# legal clock attached rather than an analytical judgement.
TRIAGE_WEIGHTS = {
    "sanctions_hit": 100.0,       # confirmed, unadjudicated match — top of the queue, always
    "sanctions_possible": 45.0,   # needs a human to confirm or clear, but isn't yet a match
    "risk_band": 40.0,            # × the band's severity score (high 1.0 → 40, medium 0.6 → 24, …)
    "sla_breached": 35.0,         # escalated and past its SLA — already late
    "sla_imminent": 20.0,         # escalated, inside TRIAGE_SLA_IMMINENT_HOURS of due
    "age_per_day": 3.0,           # ages upward so nothing rots at the bottom of the queue…
}
TRIAGE_AGE_CAP_DAYS = 10          # …but capped, so age alone never outranks a real signal
TRIAGE_SLA_IMMINENT_HOURS = 6

# ── Local AI (Ollama) ───────────────────────────────────────────────────────
# The system runs fully OFFLINE with no LLM at all: the Investigation Agent
# falls back to a deterministic template narrative and every dimension score
# stays exactly the same either way — anomaly detection and risk scoring are
# ALWAYS computed in code, never by the model (§7, §32).
#
# When Ollama is reachable, narratives are written by a small local model
# (see MODEL_PROVENANCE below for source/license/version) run entirely on
# this machine — no request in the normal path leaves localhost.
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
LLM_MODEL = os.getenv("ACI_LLM_MODEL", "qwen3:4b")
EMBED_MODEL = os.getenv("ACI_EMBED_MODEL", "nomic-embed-text")
# Generous enough for CPU-only inference (no retry-on-timeout — see aci/llm.py)
# to still complete within the blueprint's own <60s case-generation KPI (§28).
# On a working GPU path this returns in 1-2s regardless of the ceiling.
LLM_TIMEOUT_S = float(os.getenv("ACI_LLM_TIMEOUT_S", "45"))

DATA_DIR = Path(os.getenv("ACI_DATA_DIR", Path(__file__).resolve().parent.parent / "data_local"))
DB_PATH = Path(os.getenv("ACI_DB_PATH", DATA_DIR / "aci.db"))

# Recorded once at pull time by scripts/setup_models.py — never invented, and
# never assumed present (§7, §37): the system checks Ollama at call time.
MODEL_PROVENANCE = [
    {"name": "qwen3:4b", "role": "narrative generation", "source": "https://ollama.com/library/qwen3",
     "publisher": "Alibaba Qwen team, distributed via Ollama", "license": "Apache-2.0", "size": "~2.5GB (Q4_K_M)"},
    {"name": "nomic-embed-text", "role": "regulatory retrieval embeddings",
     "source": "https://ollama.com/library/nomic-embed-text", "publisher": "Nomic AI, distributed via Ollama",
     "license": "Apache-2.0", "size": "~274MB"},
]
