#!/usr/bin/env python3
"""
End-to-end demo (Blueprint §5, §29).

Runs the full multi-agent investigation on TX-84721 and prints the case report
exactly the way a compliance officer would receive it. No database or API key
required — it works offline with the deterministic template narrative, and
upgrades to an AI-written narrative automatically if a local Ollama model is
available (see aci/llm.py).

    python run_demo.py            # TX-84721
    python run_demo.py TX-90233   # structuring scenario
    python run_demo.py --eval     # run the evaluation harness
"""
import sys

from aci.console import enable_utf8_stdout

enable_utf8_stdout()

from aci.data.synthetic import seed_world  # noqa: E402
from aci.orchestrator import investigate, record_human_decision  # noqa: E402

LINE = "=" * 66
DASH = "-" * 66


def sev_bar(sev):
    return {"high": "HIGH  ", "medium": "MEDIUM", "low": "LOW   ", "none": "NONE  "}[sev.value]


def print_case(case):
    txn = case.transaction
    print(LINE)
    print("AI COMPLIANCE INVESTIGATION REPORT")
    print(LINE)
    print(f"CASE:        {case.case_id:<24} PRIORITY: {case.priority.value.upper()}")
    print(f"TRANSACTION: {txn.transaction_id}")
    print(f"CUSTOMER:    {case.customer.name}")
    print(f"AMOUNT:      INR {txn.amount:,}")
    print(f"ROUTE:       {' -> '.join(txn.route)}")
    print(f"PURPOSE:     {txn.purpose}")
    print(DASH)
    print("KEY FINDINGS")
    print(DASH)
    n = 1
    for r in case.agent_results:
        for s in r.signals:
            print(f"{n}. {s.type:<28} Severity: {sev_bar(s.severity)}  {s.explanation}")
            n += 1
        for f in r.findings:
            print(f"{n}. {f.type:<28} Severity: {sev_bar(f.severity)}  {f.description}")
            n += 1
    print(DASH)
    print("EXPLAINABLE RISK  (weighted, configurable)")
    print(DASH)
    for row in case.risk.rows:
        pct = int(row.contribution / max(row.weight, 1e-9) * 100)
        bar = "#" * (pct // 7)
        print(f"  {row.label:<26} w{row.weight:<4} {sev_bar(row.severity)}  {bar}")
    print(f"  {'OVERALL':<26}       {case.priority.value.upper()}   score {case.risk.score:.2f}/1.00")
    print(f"  {'CONFIDENCE (evidence, not fraud prob.)':<40} {case.risk.confidence:.2f}")
    print(DASH)
    print("EVIDENCE")
    print(DASH)
    for e in case.evidence:
        print(f"  {e.id}  [{e.source_type}]  {e.content}")
    print(DASH)
    print("REGULATORY CONTROLS  (retrieved with provenance — synthetic)")
    print(DASH)
    reg_result = next(r for r in case.agent_results if r.dimension == "regulatory")
    for r in reg_result.regulatory:
        print(f"  {r.id} · {r.section}  {r.title}")
        print(f"        why: {r.why}")
    print(DASH)
    print("INVESTIGATION NARRATIVE  (source: %s)" % case.narrative.source)
    print(DASH)
    for label, val in [("What happened", case.narrative.what_happened),
                       ("Why unusual", case.narrative.why_unusual),
                       ("Who involved", case.narrative.who_involved),
                       ("Conclusion", case.narrative.conclusion)]:
        print(f"  {label}: {val}")
    print(DASH)
    print("UNKNOWN INFORMATION")
    print(DASH)
    for u in case.unknowns:
        print(f"  - {u}")
    print(DASH)
    print("RECOMMENDED NEXT STEPS")
    print(DASH)
    for i, a in enumerate(case.recommended_actions, 1):
        print(f"  {i}. {a}")
    print(DASH)
    print("HUMAN DECISION  (required — the AI does not decide)")
    print(DASH)
    print("  [ ] Close   [ ] Request info   [ ] Enhanced due diligence   [ ] Escalate")
    print(LINE)


def main():
    args = sys.argv[1:]
    if "--eval" in args:
        from aci.evaluation.evaluate import evaluate
        import json
        print("Evaluation over synthetic population (§28):")
        print(json.dumps(evaluate(), indent=2))
        return
    tid = next((a for a in args if a.startswith("TX-")), "TX-84721")
    world = seed_world()
    case = investigate(tid, world)
    print_case(case)
    # Simulate the human making the call — the only decision point.
    record_human_decision(case, actor="s.compliance", decision="edd",
                          note="Request UBO verification and detailed engagement contract.")
    print("\nAUDIT TRAIL")
    print(DASH)
    for a in case.audit:
        print(f"  {a.timestamp.strftime('%H:%M:%S')}  {a.actor:<12} {a.action}")


if __name__ == "__main__":
    main()
