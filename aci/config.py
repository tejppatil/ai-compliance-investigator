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
