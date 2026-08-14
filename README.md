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
pytest -q                          # 54 tests incl. red-team, prompt injection, two-tier escalation, hash-chain integrity
```

**Without Ollama it still works.** Narratives fall back to a deterministic
template; every risk score, finding, citation and evidence item is byte-identical,
because none of them are produced by the model.

The web console opens on a combined **Risk-Based Approach + sign-in page** —
the methodology, a live weight chart, and the FATF R.1 citation, with a
demo sign-in (name + role, no password) below it. This is a presentational
demo mechanism, not real authentication — see "What makes it trustworthy"
below for what's actually enforced server-side.

> **Port note:** the API defaults to **8077**, not 8000 — the Ollama desktop app
> binds 8000 on Windows.

---

## The investigation pipeline

```
Transaction → Customer history → Transaction Intelligence → Entity Intelligence
  → Compliance Intelligence (RAG) → Document Analysis → KYC Completeness
  → Risk Engine (incl. customer risk rating) → Evidence correlation → Investigation narrative
  → TIER-1 HUMAN REVIEW → (optional) ESCALATION → TIER-2 SENIOR REVIEW → Audit trail
```

Every case page shows this exact sequence as a live, animating diagram (`PipelineFlow`, driven by
real case state) — open any transaction and click **Run investigation** to watch it move stage by
stage instead of a score just appearing. A static version lives on its own **How it works** page.

| Agent | File | What it does |
|---|---|---|
| Transaction Intelligence | `aci/agents/transaction_agent.py` | Median, ratio, velocity, structuring, layering — **pure statistics, no LLM** |
| Entity Intelligence | `aci/agents/entity_agent.py` | Common directors, UBO chains. Never asserts wrongdoing |
| Compliance Intelligence | `aci/agents/compliance_agent.py` + `aci/rag/` | Jurisdiction-filtered retrieval with full provenance |
| Document Analysis | `aci/agents/document_agent.py` | Invoice ↔ transaction reconciliation, incl. amount mismatch |
| KYC Completeness | `aci/agents/kyc_agent.py` | Onboarding-record consistency (name match, ownership completeness, date sanity) — a data-quality check, kept **out of** the risk score on purpose |
| Risk Engine | `aci/agents/risk_agent.py` | Six-dimension Risk-Based Approach; each row traces to the finding IDs behind it |
| Investigation Agent | `aci/agents/investigation_agent.py` + `aci/llm.py` | Correlates everything; builds the evidence graph and timeline |
| **Tier-1 review** | `orchestrator.record_human_decision` (role=officer) | Close, request info/EDD, or escalate — **the only place a decision enters the system** |
| **Tier-2 senior review** | `orchestrator.record_human_decision` (role=senior) | Only reachable once escalated; approve, override, or return — enforced server-side |

Orchestration is a controlled pipeline (`aci/orchestrator.py`), not free-roaming
agents. Every agent returns the same `AgentResult` contract (`aci/models.py`).

Every deterministic rule any agent runs is catalogued in one place —
`aci/rules_catalog.py`, browsable on the **Detection rules** page — with its real threshold pulled
live from `aci/config.py`, not a paraphrase that could drift from the code.

---

## What makes it trustworthy

- **Deterministic maths.** Anomaly detection and risk scoring run in Python.
  The LLM only narrates, and it never decides.
- **Risk-Based Approach.** Six weighted dimensions — transaction behaviour,
  entity/ownership, regulation, documentation, geography, and the customer's
  own *persistent* risk rating — implementing FATF Recommendation 1 (real
  citation, see `FATF-R1` in the KB). A customer's risk rating alone can drive
  a case to review even when the transaction itself is unremarkable; see
  `TX-31204` in the demo queue for a case built to show exactly that in
  isolation.
- **Two-person integrity control.** Escalating a case (`aci/orchestrator.py`
  `record_human_decision`) assigns it to a named Senior Compliance Officer
  with a 24h SLA. A tier-1 officer's attempt to re-decide an already-escalated
  case is rejected with a real HTTP 403 — enforced server-side, not just a
  disabled button — until the senior approves, overrides, or returns it for
  more evidence. The console's persona switcher is a labelled demo mechanism
  for trying both sides without two logins; the control it exercises is real.
- **Real, checkable regulation.** Real, source-linked documents from RBI, IFSCA,
  CBUAE, MAS and FATF, each with `source_url`, publication date and version.
  Summaries are our own paraphrase, never quoted statute text. Below a
  relevance floor the system says *"Insufficient information in the configured
  regulatory knowledge base."* rather than reaching for a weak match. See
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
- **Tamper-evident audit trail.** Every audit entry is SHA-256 hash-chained to
  the one before it (`aci/db.py` `verify_audit_chain`) — editing or
  reordering a past entry breaks every hash after it. `GET
  /api/audit/{case_id}/verify` recomputes the chain on demand; the case
  page shows the live result as a badge, not a claim.
- **Persistent audit trail.** Cases and every action survive a restart —
  including escalation assignment and SLA, which migrate onto a database
  created before this feature existed rather than requiring a wipe.
- **Network insight across cases.** The same director/beneficial-owner entity
  showing up in more than one *different* customer's case is surfaced on the
  dashboard (`aci/db.py` `network_insights`) — computed from evidence graphs
  already persisted, no graph database required.
- **Prove it on a transaction nobody staged.** The **New transaction** page
  submits a real transaction to a brand-new beneficiary and investigates it
  through the identical pipeline live — the signals it trips (or doesn't) are
  genuinely computed, not scripted for a demo.

---

## Measured results

`python run_demo.py --eval` over 5,000 synthetic transactions (seed 7):

| Metric | Value |
|---|---|
| Precision | 0.569 |
| Recall | 1.000 |
| F1 | 0.726 |
| False-positive rate | 0.189 |
| Mean case time | 11.1 ms (deterministic path, five agents) |
| Per-scenario detection | 1.000 across all 8 anomalous scenarios |

Tuned for recall: in AML triage a missed case costs more than an extra review.
The `normal` population contains deliberate near-misses (legitimate spikes,
genuinely new counterparties, and — since adding the Risk-Based Approach
dimension — a small fraction of otherwise-normal customers with an elevated
persistent risk rating). That last group is precision's real cost here: an
RBA system is *supposed* to flag more cases for a customer it already
considers higher-risk, even when nothing else is wrong, and this dataset
reflects that honestly rather than hiding it. An earlier generator with none
of this near-miss population scored a meaningless F1 of 1.000. Reproduce with
the command above; nothing here is hand-tuned for presentation.

Case generation with the local LLM narrative takes ~25 s on CPU-only inference,
within the project's <60 s target. On a working CUDA path it is 1–2 s.

---

## API

```
GET  /api/dashboard                          aggregate KPIs
GET  /api/transactions                       demo queue
GET  /api/customers                          existing demo customers (New Transaction form)
POST /api/transactions                       submit a new transaction to a fresh beneficiary
POST /api/investigations                     {"transaction_id": "TX-84721"}
GET  /api/investigations                     all persisted cases
GET  /api/investigations/{case_id}           full case
     .../findings | .../evidence | .../graph
POST /api/investigations/{case_id}/review    tier 1: {"decision":"edd|escalate|info|close","role":"officer"}
                                              tier 2: {"decision":"senior_close|senior_override|senior_return","role":"senior"}
                                              — a tier-1 decision on an already-escalated case returns HTTP 403
GET  /api/escalations                        cases awaiting the senior reviewer, with SLA + overdue flag
GET  /api/network-insights                   entities shared across different customers' cases
GET  /api/risk-methodology                   RBA weights, dimension descriptions, policy table
GET  /api/rules                              the full detection-rule catalogue
GET  /api/regulations | /api/regulations/search?q=...
GET  /api/audit/{case_id}                    one case's audit trail
GET  /api/audit/{case_id}/verify             tamper-evident hash-chain check
GET  /api/audit                              recent activity across all cases
GET  /api/status                             local model + provenance
```

Interactive docs at `http://127.0.0.1:8077/docs`.

---

## Second module: Cyber Crime & Financial Fraud Investigation

A separate law-enforcement console sharing the same login, for a different
user and a different problem: live transaction monitoring and multi-officer
case command, rather than corporate cross-border AML case files. Sign in as
one of the three Cyber Crime Unit roles to enter it.

| Role | Lands on | Sees |
|---|---|---|
| Nodal / Escalation Lead | Command Center | Every officer's status, assignment and last action; escalate or transfer any case |
| Investigation Officer (IO) | Case Ops | The layering flow — source → mule → mule → cash-out — with a per-hop holding-freeze action |
| Bank Fraud / Cyber Cell Analyst | Transaction Feed | The live stream with rule-engine flags and a velocity chart |

Also available to all three: a **geographic heat map** (filterable by
timeframe, crime type and severity) and an **intelligence link network**
connecting suspect, financial and spatial entities, each node opening a
detail drawer with its confidence score and raw indicators.

```
GET  /api/cyber/officers | /cases | /cases/{id}
POST /api/cyber/cases/{id}/escalate      {"officer_name","note"}
POST /api/cyber/cases/{id}/transfer      {"new_officer_id","actor_name"}
POST /api/cyber/cases/{id}/freeze-hop    {"hop_index","officer_name"}
POST /api/cyber/transactions/{id}/freeze {"officer_name"}
GET  /api/cyber/transactions/recent | /geo-incidents | /graph/{case_id}
WS   /ws/cyber/transactions               live feed
```

**The feed is a real WebSocket, not polling.** A server-side simulator
(`aci/cybercrime/simulator.py`) generates a transaction every ~2.5s and
pushes it to every connected client; it builds genuine multi-hop layering
chains and velocity bursts over successive ticks, so the rule engine
(`aci/cybercrime/rules.py`) has real patterns to catch rather than
pre-labelled ones. Every flag names the threshold it crossed — known mule
account, layering depth, velocity window, high-risk cash-out location,
single-transfer value — the same "no unexplained scores" rule the compliance
module holds itself to.

**Freezes are officer actions, never automatic.** The rule engine flags and
raises alerts; a human clicks the freeze, and it's written to the case
history attributed by name. Same boundary as *AI investigates, human
decides* on the compliance side.

**One caveat, stated plainly:** the heat map's basemap tiles are fetched from
a public CDN — the only part of this project that touches the internet at
runtime. Offline, the map renders blank tiles while every marker, filter and
count still works, because those come from our own API.

---

## Layout

```
aci/
  models.py          agent contracts + domain records
  config.py          thresholds, documented risk weights, RBA policy table
  orchestrator.py    controlled pipeline + the human decision point
  llm.py             local Ollama provider, validation, template fallback
  db.py              SQLite persistence (self-healing schema, hash-chain, network insights)
  rules_catalog.py   the full detection-rule reference, thresholds pulled live from config
  agents/            transaction · entity · compliance · document · kyc · risk · investigation
  rag/               regulatory KB + hybrid (dense + TF-IDF) retriever
  evaluation/        precision/recall/F1, reported per scenario
  api/app.py         FastAPI endpoints (+ cybercrime_routes.py)
  data/synthetic.py  seeded demo world + labelled bulk generator
  cybercrime/        second module — models · deterministic rules · live
                     simulator · in-memory officer/case store · seed data
frontend/            React + Vite console (VIGILO theme + Recharts), incl.
                     persona.jsx (login/session, 5 roles across 2 modules),
                     PipelineFlow.jsx (live + static pipeline diagram),
                     InvestigationTimeline.jsx, the RBA landing/login page,
                     and cybercrime/ (command center · case ops · live feed ·
                     Leaflet heat map · intelligence graph)
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
regulatory KB is eleven documents for one corridor, not comprehensive coverage.

What it does demonstrate is the **investigation journey** and the architecture
around it: gather → correlate → explain → cite → hand to a human.

The KYC completeness check, the detection-rules catalogue, the tamper-evident
hash-chained audit log, and the maker-checker-style two-tier escalation are
original implementations for this project's actual domain (B2B cross-border
AML investigation), inspired by patterns in two prior hackathon projects —
[Trustsphere](https://github.com/Muditsrivastav21/Trustsphere) and
[Finspark/Prahari](https://github.com/tejppatil/Finspark-Bank-of-Maharashtra)
— not copied from either; neither is a dependency of this project. Retail
biometric KYC (OCR/face-match) and a graph database were deliberately left
out as the wrong tool for this domain — see `aci/agents/kyc_agent.py` and
`aci/db.py network_insights()` for what was built instead and why.

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
