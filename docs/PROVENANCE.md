# Provenance

Everything this system downloads or cites, with source, licence and the date it
was verified. Nothing here is redistributed in this repository — models are
pulled at setup time, and regulatory documents are cited by URL rather than
copied.

---

## Local models

Pulled by `scripts/setup.py` via [Ollama](https://ollama.com). Both run entirely
on the local machine; no inference request leaves `localhost`.

| Model | Role | Publisher | Licence | Size | Source | Pulled |
|---|---|---|---|---|---|---|
| `qwen3:4b` | Investigation narrative generation | Alibaba Qwen team, distributed via Ollama | Apache-2.0 | ~2.5 GB (Q4_K_M) | https://ollama.com/library/qwen3 | 2026-08-13 |
| `nomic-embed-text` | Regulatory retrieval embeddings | Nomic AI, distributed via Ollama | Apache-2.0 | ~274 MB | https://ollama.com/library/nomic-embed-text | 2026-08-13 |

**Why these sizes.** The target machine has an RTX 3050 with 6 GB VRAM. A 4B
model at Q4_K_M leaves headroom for context; a 7B+ model would not fit reliably
alongside the desktop compositor. The system also runs correctly with no model
at all — see "Degradation" below.

**Degradation.** If Ollama is unreachable, the model is missing, or generation
times out, the Investigation Agent falls back to a deterministic template
narrative. Risk scores, findings, evidence and citations are **identical** in
both cases, because none of them are produced by the model.

---

## Regulatory knowledge base

Defined in `aci/rag/knowledge_base.py`. Each entry is a real, publicly issued
regulatory document. `summary` fields are this project's own paraphrase written
for retrieval — **not quoted statute text**. Where a specific internal section
number could not be independently verified, `section` records `"Full document"`
rather than guessing, because a wrong section number is indistinguishable from
a fabricated one.

| ID | Document | Regulator | Jurisdiction | Verified |
|---|---|---|---|---|
| `IN-RBI-KYC-2025` | RBI (Commercial Banks – Know Your Customer) Directions, 2025 | Reserve Bank of India | India | 2026-08-12, fetched from rbi.org.in |
| `IN-RBI-LRS` | Master Direction – Liberalised Remittance Scheme | RBI, Foreign Exchange Dept. | India | 2026-08-12, RBI FED master-direction reference |
| `IN-PMLA-S12` | Prevention of Money-Laundering Act, 2002 — Section 12 | FIU-IND / Dept. of Revenue | India | 2026-08-12, cross-checked vs FIU-IND text |
| `IFSCA-AML-2022` | IFSCA (AML, CFT and KYC) Guidelines, 2022 | IFSCA | GIFT IFSC | 2026-08-12, fetched from ifsca.gov.in |
| `AE-AML-FDL10-2025` | Federal Decree by Law No. (10) of 2025 (AML/CFT/PF) | UAE Federal Government | UAE | 2026-08-12, uaelegislation.gov.ae + legal alerts |
| `AE-CBUAE-GUIDANCE` | CBUAE Guidance for Licensed Financial Institutions on AML/CFT/CPF | Central Bank of the UAE | UAE | 2026-08-12, rulebook.centralbank.ae |
| `SG-MAS-N626` | MAS Notice 626 — Prevention of ML and CFT – Banks | Monetary Authority of Singapore | Singapore | 2026-08-12, mas.gov.sg notice listing |
| `FATF-R10` | FATF Recommendation 10 — Customer Due Diligence | FATF | International | 2026-08-12 |
| `FATF-R16` | FATF Recommendation 16 — Wire Transfers | FATF | International | 2026-08-12 |
| `FATF-R24` | FATF Recommendation 24 — Beneficial Ownership of Legal Persons | FATF | International | 2026-08-12 |
| `FATF-R1` | FATF Recommendation 1 — Assessing Risks and Applying a Risk-Based Approach | FATF | International | 2026-08-13, cross-checked against FATF/CFATF sources |

**A note on verification method.** `rbi.org.in` and `ifsca.gov.in` were fetched
directly. `centralbank.ae`, `mas.gov.sg` and `fatf-gafi.org` returned 403 or
service-unavailable responses to automated requests, so those entries were
cross-checked against the regulators' own listing pages plus independent legal
reporting. Every entry carries a `source_url` a reviewer can open and check.

**What this is not.** Eleven documents is a demonstration corpus for one corridor,
not comprehensive regulatory coverage. Retrieval is filtered to the
transaction's own jurisdictions; below a relevance floor the system returns
*"Insufficient information in the configured regulatory knowledge base."*
rather than a weak match.

---

## Synthetic dataset

Generated locally by `aci/data/synthetic.py`; exportable via
`scripts/export_dataset.py`. See `docs/DATASET_CARD.md`.

**No real, confidential, or leaked financial data is used anywhere in this
project.** Customers, entities, directors, transactions and invoices are all
programmatically generated from a fixed seed.
