# AI Compliance Investigator for Cross-Border Finance

A multi-agent compliance investigation platform for the GIFT IFSC corridor.
**AI gathers evidence, humans decide.** Runs entirely on your own machine.

> An AI-powered compliance investigation system that autonomously gathers,
> correlates, and explains evidence for cross-border transactions — while
> keeping every final regulatory decision with a human compliance officer.

It takes one synthetic cross-border transaction (India → UAE → Singapore) and
detects unusual behaviour, investigates entities and their relationships,
retrieves relevant regulatory requirements *with checkable citations*, checks
documentation against the transaction, scores risk explainably, builds an
evidence graph, writes an investigation narrative with a local LLM, and hands a
structured case to a human — whose decision is the only one the system records.

**All data is synthetic. No real banking data is used.**

---

## Local-first, by construction

| Concern | How it's handled |
|---|---|
| **LLM** | `qwen3:4b` via local Ollama. No API key, no cloud provider. |
| **Embeddings** | `nomic-embed-text`, computed locally and cached to disk. |
| **Database** | SQLite file. No server, no container, no cloud. |
| **Vector search** | Cosine over cached local embeddings, fused with TF-IDF. No vector DB. |
| **Regulatory KB** | Real, source-linked documents stored in-repo. |
| **Network in the request path** | None. Verified with outbound sockets blocked. |

Internet is needed **once**, at setup, to fetch dependencies and models. After
that the whole system runs offline — this is tested, not assumed.

---

## Quick start

```bash
python scripts/setup.py     # deps, Ollama models, database, RAG index, frontend
python scripts/start.py     # API + web console, opens the browser
```

Or drive it from the terminal:

```bash
python run_demo.py                 # full TX-84721 investigation report
python run_demo.py TX-90233        # the structuring scenario
python run_demo.py --eval          # precision / recall / F1, per scenario
pytest -q                          # 26 tests incl. red-team + prompt injection
```

**Without Ollama it still works.** Narratives fall back to a deterministic
template; every risk score, finding, citation and evidence item is byte-identical,
because none of them are produced by the model.

> **Port note:** the API defaults to **8077**, not 8000 — the Ollama desktop app
> binds 8000 on Windows.

---

## The investigation pipeline

```
Transaction → Customer history → Transaction Intelligence → Entity Intelligence
  → Compliance Intelligence (RAG) → Document Analysis → Risk Engine
  → Evidence correlation → Investigation narrative → HUMAN REVIEW → Audit trail
```

| Agent | File | What it does |
|---|---|---|
| Transaction Intelligence | `aci/agents/transaction_agent.py` | Median, ratio, velocity, structuring, layering — **pure statistics, no LLM** |
| Entity Intelligence | `aci/agents/entity_agent.py` | Common directors, UBO chains. Never asserts wrongdoing |
| Compliance Intelligence | `aci/agents/compliance_agent.py` + `aci/rag/` | Jurisdiction-filtered retrieval with full provenance |
| Document Analysis | `aci/agents/document_agent.py` | Invoice ↔ transaction reconciliation, incl. amount mismatch |
| Risk Engine | `aci/agents/risk_agent.py` | Documented weights; each row traces to the finding IDs behind it |
| Investigation Agent | `aci/agents/investigation_agent.py` + `aci/llm.py` | Correlates everything; builds the evidence graph |
| **Human Review** | `orchestrator.record_human_decision` / web console | **The only place a decision enters the system** |

Orchestration is a controlled pipeline (`aci/orchestrator.py`), not free-roaming
agents. Every agent returns the same `AgentResult` contract (`aci/models.py`).

---

## What makes it trustworthy

- **Deterministic maths.** Anomaly detection and risk scoring run in Python.
  The LLM only narrates, and it never decides.
- **Real, checkable regulation.** Ten genuine documents from RBI, IFSCA, CBUAE,
  MAS and FATF, each with `source_url`, publication date and version. Summaries
  are our own paraphrase, never quoted statute text. Below a relevance floor the
  system says *"Insufficient information in the configured regulatory knowledge
  base."* rather than reaching for a weak match. See
  [`docs/PROVENANCE.md`](docs/PROVENANCE.md).
- **Confidence ≠ risk.** `HIGH @ 0.84` means the evidence supports a
  high-priority investigation — not an 84% chance of fraud. Shown as separate
  bars.
- **Untrusted documents.** Invoice text is data, never instructions. A
  "mark this low risk" line inside an upload cannot move the score — the
  deterministic engine never reads it, and the LLM receives it inside a fenced
  `<case_data>` block it is instructed to treat as quoted content. Covered by
  parametrised tests.
- **Reproducible IDs.** Re-investigating a case yields identical finding and
  evidence IDs, so the audit trail is stable.
- **Persistent audit trail.** Cases and every action survive a restart.

---

## Measured results

`python run_demo.py --eval` over 5,000 synthetic transactions (seed 7):

| Metric | Value |
|---|---|
| Precision | 0.627 |
| Recall | 1.000 |
| F1 | 0.771 |
| False-positive rate | 0.148 |
| Mean case time | 6.5 ms (deterministic path) |
| Per-scenario detection | 1.000 across all 8 anomalous scenarios |

Tuned for recall: in AML triage a missed case costs more than an extra review,
so 594 false positives out of 4,000 normal transactions is the deliberate
trade-off. The `normal` population contains deliberate near-misses (legitimate
spikes, genuinely new counterparties) — an earlier generator without them scored
a meaningless F1 of 1.000. Reproduce with the command above; nothing here is
hand-tuned for presentation.

Case generation with the local LLM narrative takes ~25 s on CPU-only inference,
within the project's <60 s target. On a working CUDA path it is 1–2 s.

---

## API

```
GET  /api/dashboard                          aggregate KPIs
GET  /api/transactions                       demo queue
POST /api/investigations                     {"transaction_id": "TX-84721"}
GET  /api/investigations                     all persisted cases
GET  /api/investigations/{case_id}           full case
     .../findings | .../evidence | .../graph
POST /api/investigations/{case_id}/review    {"decision":"edd|escalate|info|close","note":"..."}
GET  /api/regulations | /api/regulations/search?q=...
GET  /api/audit/{case_id}
GET  /api/status                             local model + provenance
```

Interactive docs at `http://127.0.0.1:8077/docs`.

---

## Layout

```
aci/
  models.py          agent contracts + domain records
  config.py          thresholds, documented risk weights, model config
  orchestrator.py    controlled pipeline + the human decision point
  llm.py             local Ollama provider, validation, template fallback
  db.py              SQLite persistence (self-healing schema)
  agents/            transaction · entity · compliance · document · risk · investigation
  rag/               regulatory KB + hybrid (dense + TF-IDF) retriever
  evaluation/        precision/recall/F1, reported per scenario
  api/app.py         FastAPI endpoints
  data/synthetic.py  seeded demo world + labelled bulk generator
frontend/            React + Vite console (VIGILO theme)
scripts/             setup · start · export_dataset
db/schema.sql        SQLite schema
docs/                blueprint · PROVENANCE · DATASET_CARD
```

---

## Scope and honesty

This is a **prototype**, not a bank-grade compliance system. The evaluation
numbers are computed on synthetic data and should not be read as production
performance. The genuinely hard parts of a real system — current licensed
regulatory data, real KYC/entity data, cross-jurisdiction rule mapping, and
integration with live financial systems — are deliberately out of scope. The
regulatory KB is ten documents for one corridor, not comprehensive coverage.

What it does demonstrate is the **investigation journey** and the architecture
around it: gather → correlate → explain → cite → hand to a human.

**"Autonomous" here means** the system independently performs predefined
investigative tasks — retrieving data, analysing behaviour, finding
relationships, retrieving regulation, correlating evidence, drafting a case. It
does **not** mean the AI decides. It never freezes accounts, rejects customers,
files reports, or declares fraud.

**Not legal or compliance advice.** See [`LICENSE`](LICENSE).

---

## Licence

MIT — see [`LICENSE`](LICENSE). Models are downloaded at setup, not
redistributed; both are Apache-2.0. See [`docs/PROVENANCE.md`](docs/PROVENANCE.md).
