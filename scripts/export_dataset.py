#!/usr/bin/env python3
"""
Export the synthetic dataset to CSV (for the Kaggle dataset card).

    python scripts/export_dataset.py                     # defaults
    python scripts/export_dataset.py --normal 4000 --anomalous 1000

Everything written is SYNTHETIC, generated locally by aci/data/synthetic.py.
No real, confidential, or leaked financial data is involved at any point.

`scenario_type` is the ground-truth label. It exists for evaluation only and
is never shown to an agent during inference (§19) — anyone training on this
data should treat it as the target, not a feature.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from aci.console import enable_utf8_stdout  # noqa: E402
from aci.data.synthetic import generate_bulk  # noqa: E402

enable_utf8_stdout()


def export(out_dir: Path, n_normal: int, n_anomalous: int, seed: int) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    world = generate_bulk(n_normal=n_normal, n_anomalous=n_anomalous, seed=seed)

    def write(name: str, header: list[str], rows) -> None:
        path = out_dir / name
        with path.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(header)
            w.writerows(rows)
        print(f"  {name:<24} {sum(1 for _ in rows) if isinstance(rows, list) else '?':>7} rows")

    write("customers.csv", ["customer_id", "name", "country", "industry", "risk_profile", "onboarded", "entity_id"],
          [[c.customer_id, c.name, c.country, c.industry, c.risk_profile, c.onboarded, c.entity_id or ""]
           for c in world.customers.values()])

    write("entities.csv", ["entity_id", "name", "entity_type", "country", "registered", "directors"],
          [[e.entity_id, e.name, e.entity_type, e.country, e.registered or "", "|".join(e.directors)]
           for e in world.entities.values()])

    write("relationships.csv", ["src", "tgt", "relationship_type", "confidence", "source"],
          [[r.src, r.tgt, r.relationship_type, r.confidence, r.source] for r in world.relationships])

    write("transactions.csv",
          ["transaction_id", "customer_id", "amount", "currency", "source_country", "destination_country",
           "ultimate_destination", "beneficiary_id", "beneficiary_registered", "timestamp", "purpose",
           "route", "scenario_type"],
          [[t.transaction_id, t.customer_id, t.amount, t.currency, t.source_country, t.destination_country,
            t.ultimate_destination, t.beneficiary_id, t.beneficiary_registered, t.timestamp, t.purpose,
            "|".join(t.route), t.scenario_type] for t in world.transactions.values()])

    write("transaction_history.csv", ["customer_id", "amount", "dest", "date"],
          [[cid, h["amount"], h["dest"], h["date"]] for cid, hist in world.history.items() for h in hist])

    write("documents.csv", ["transaction_id", "doc_type", "narrative", "amount", "currency"],
          [[d.transaction_id, d.doc_type, d.narrative, d.amount, d.currency] for d in world.documents.values()])


def main() -> None:
    p = argparse.ArgumentParser(description="Export the synthetic dataset to CSV.")
    p.add_argument("--out", default=str(ROOT / "data_local" / "dataset_csv"))
    p.add_argument("--normal", type=int, default=4000)
    p.add_argument("--anomalous", type=int, default=1000)
    p.add_argument("--seed", type=int, default=7)
    args = p.parse_args()

    out = Path(args.out)
    print(f"Generating synthetic dataset (normal={args.normal}, anomalous={args.anomalous}, seed={args.seed})…")
    export(out, args.normal, args.anomalous, args.seed)
    print(f"\nWritten to {out}")
    print("All data is synthetic. scenario_type is the evaluation label — never an input feature.")


if __name__ == "__main__":
    main()
