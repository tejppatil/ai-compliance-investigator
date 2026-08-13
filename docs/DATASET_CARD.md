# Dataset Card — Synthetic Cross-Border Compliance Investigation Dataset

A fully synthetic dataset of cross-border financial transactions along the
India ↔ UAE ↔ Singapore corridor, labelled with AML/CFT risk-indicator
scenarios, for research on compliance investigation and explainable anomaly
detection.

Generate it yourself:

```bash
python scripts/export_dataset.py --normal 4000 --anomalous 1000
```

---

## ⚠️ Read this first

- **Entirely synthetic.** Every customer, company, director, transaction and
  invoice is programmatically generated from a fixed random seed. **No real,
  confidential, or leaked financial data is used.** Any resemblance to a real
  person or company is coincidental.
- **Labels are risk indicators, not proof of crime.** A `scenario_type` of
  `structuring` means the record was *generated to exhibit a pattern that
  warrants investigation* — not that a crime occurred. Real AML work treats
  these as triggers for human review, and so should any model trained here.
- **`scenario_type` is the target, never a feature.** It is ground truth for
  evaluation only and is never exposed to the investigating agents at inference
  time.
- **Not a benchmark for real-world performance.** The generator injects
  overlap and noise deliberately (see below), but synthetic separability is
  still not real-world separability.

---

## Contents

At the default size (`--normal 4000 --anomalous 1000`):

| File | Rows | Description |
|---|---:|---|
| `customers.csv` | 5,000 | Customer profiles, each linked to a corporate `entity_id` |
| `entities.csv` | 15,000 | Companies and individuals (directors, beneficial owners, counterparties) |
| `relationships.csv` | 5,250 | Typed edges: `director_of`, `beneficial_owner_of`, with confidence + source |
| `transactions.csv` | 5,000 | Cross-border transactions, labelled with `scenario_type` |
| `transaction_history.csv` | 35,125 | Per-customer historical behaviour — the baseline anomalies are measured against |
| `documents.csv` | 4,875 | Invoices (fewer than transactions: the `missing_documentation` scenario has none) |

### Scenario distribution

| `scenario_type` | Count | What it exhibits |
|---|---:|---|
| `normal` | 4,000 | Baseline activity, including deliberate noise (see below) |
| `amount_anomaly` | 125 | Transaction 3.2–8× the customer's own historical median |
| `new_counterparty` | 125 | Beneficiary registered shortly before the transaction |
| `relationship_anomaly` | 125 | Common director between sender-side and beneficiary-side entities |
| `structuring` | 125 | Repeated transfers just below a reporting threshold |
| `documentation_anomaly` | 125 | Invoice narrative generic relative to the value |
| `missing_documentation` | 125 | No supporting document at all |
| `rapid_movement` | 125 | Elevated velocity combined with multi-hop routing (layering) |
| `multi_signal` | 125 | Several of the above at once |

### Deliberate noise in the `normal` class

An earlier version of this generator produced trivially separable data and
scored a meaningless F1 of 1.000. The `normal` population now includes:

- ~8% of customers with a legitimate seasonal spike (1.3–1.7×, capped below
  the 1.8× anomaly threshold)
- ~15% with a genuinely new but unremarkable counterparty

This is what produces a realistic false-positive rate instead of a perfect
score, and it is the point: an AML system's hard problem is false positives,
so a dataset without near-misses cannot measure the thing that matters.

---

## Baseline results

Measured on the full 5,000-transaction set with the deterministic rule-based
engine in this repository (`python run_demo.py --eval`), seed 7:

| Metric | Value |
|---|---|
| Precision | 0.627 |
| Recall | 1.000 |
| F1 | 0.771 |
| False-positive rate | 0.148 |
| True pos / False pos | 1,000 / 594 |
| True neg / False neg | 3,406 / 0 |
| Mean case time | 6.5 ms |

Per-scenario detection is 1.000 for all eight anomalous scenarios; specificity
on `normal` is 0.852.

**How to read this.** The engine is tuned for recall — in AML triage a missed
case costs more than an extra review — so precision is the trade-off, and 594
false positives out of 4,000 normal transactions is the honest cost of that
choice. These are not tuned-for-publication numbers; reproduce them with the
command above.

---

## Schema notes

- `route` is pipe-delimited (`India|UAE|Singapore`).
- `directors` in `entities.csv` is pipe-delimited entity IDs.
- Amounts are integer INR (no minor units).
- `relationships.csv` carries `confidence` and `source` because provenance is
  first-class in this project — an unverified UBO filing should not be treated
  like a corporate-registry record.

## Licence

MIT, same as the parent repository. Generated data carries no third-party
rights.

## Citation

```
AI Compliance Investigator — Synthetic Cross-Border Compliance
Investigation Dataset (2026). Generated with aci/data/synthetic.py.
https://github.com/tejppatil/ai-compliance-investigator
```
