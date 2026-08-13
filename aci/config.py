"""Central configuration. Values are documented so an evaluator can see exactly
why a case lands where it does (§10, §18)."""
import os
from pathlib import Path

# Deterministic anomaly thresholds
AMOUNT_RATIO_HIGH = 3.0        # amount / historical median >= this -> HIGH
AMOUNT_RATIO_MEDIUM = 1.8
NEW_COUNTERPARTY_MONTHS = 6    # beneficiary onboarded within N months -> flag
REPORTING_THRESHOLD = 1_000_000  # synthetic INR reporting threshold (structuring)
STRUCTURING_BAND = 0.90        # transfers in [threshold*band, threshold) count as near-threshold
VELOCITY_MULTIPLIER = 2.0

# Explainable risk weights (must sum to 1.0). Configurable & visible (§10).
RISK_WEIGHTS = {
    "transaction": 0.30,
    "entity": 0.25,
    "regulatory": 0.20,
    "documentation": 0.15,
    "jurisdiction": 0.10,
}
assert abs(sum(RISK_WEIGHTS.values()) - 1.0) < 1e-9, "risk weights must sum to 1.0"

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
