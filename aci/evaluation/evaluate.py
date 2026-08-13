"""
Evaluation framework (§28).

Runs the orchestrator over a labelled synthetic population and measures
detection quality. A transaction is a positive prediction if the risk band is
MEDIUM/HIGH; ground truth positive if scenario_type != 'normal'. The label is
used ONLY here — never passed to an agent during inference (§19).

Reports metrics both in aggregate AND per scenario type. An aggregate F1 can
hide a dimension that detects nothing — that is exactly what happened here:
Entity Intelligence had 0% recall on every relationship_anomaly case until the
sender-matching bug in aci/agents/entity_agent.py was fixed, and the aggregate
score never surfaced it. Numbers below are whatever the run actually produces;
none of this is a target to hit (§31).
"""
from __future__ import annotations

import time
from collections import defaultdict

from aci.data.synthetic import generate_bulk
from aci.models import Severity
from aci.orchestrator import investigate


def _prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return round(precision, 3), round(recall, 3), round(f1, 3)


def evaluate(n_normal: int = 400, n_anomalous: int = 200, seed: int = 7) -> dict:
    world = generate_bulk(n_normal=n_normal, n_anomalous=n_anomalous, seed=seed)
    tp = fp = tn = fn = 0
    times: list[float] = []
    evidence_counts: list[int] = []
    citation_counts: list[int] = []
    per_scenario: dict[str, dict[str, int]] = defaultdict(lambda: {"n": 0, "correct": 0})

    for tid in list(world.transactions):
        start = time.perf_counter()
        case = investigate(tid, world, use_ai_narrative=False)  # risk band is identical either way; skip the LLM call
        times.append(time.perf_counter() - start)
        evidence_counts.append(len(case.evidence))
        reg = next(r for r in case.agent_results if r.dimension == "regulatory")
        citation_counts.append(len(reg.regulatory))

        predicted_positive = case.risk.band in (Severity.HIGH, Severity.MEDIUM)
        scenario = world.transactions[tid].scenario_type
        actual_positive = scenario != "normal"

        per_scenario[scenario]["n"] += 1
        if predicted_positive == actual_positive:
            per_scenario[scenario]["correct"] += 1

        if predicted_positive and actual_positive: tp += 1
        elif predicted_positive and not actual_positive: fp += 1
        elif not predicted_positive and not actual_positive: tn += 1
        else: fn += 1

    precision, recall, f1 = _prf(tp, fp, fn)
    fpr = fp / (fp + tn) if (fp + tn) else 0.0

    # For "normal" this is specificity (1 - false-positive rate on that group);
    # for every anomalous scenario_type it is that pattern's own recall.
    by_scenario = {
        scenario: {"n": v["n"], "detection_rate": round(v["correct"] / v["n"], 3) if v["n"] else 0.0}
        for scenario, v in sorted(per_scenario.items())
    }

    return {
        "n": len(world.transactions), "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "precision": precision, "recall": recall, "f1": f1,
        "false_positive_rate": round(fpr, 3),
        "avg_case_ms": round(1000 * sum(times) / len(times), 1),
        "max_case_ms": round(1000 * max(times), 1),
        "avg_evidence_per_case": round(sum(evidence_counts) / len(evidence_counts), 1),
        "avg_regulatory_citations_per_case": round(sum(citation_counts) / len(citation_counts), 1),
        "by_scenario_detection_rate": by_scenario,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(evaluate(), indent=2))
