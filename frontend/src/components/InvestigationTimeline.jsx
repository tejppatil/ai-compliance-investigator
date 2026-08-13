import React from "react";

// Reconstructs "what happened, how it happened" as a chronological story from
// data the API already returns — no new backend endpoint. Onboarding date and
// beneficiary registration come from the case's transaction/customer records;
// every investigation step and human decision comes from the real audit
// trail (aci/orchestrator.py appends one entry per pipeline stage and per
// human action), so this is a visualisation of real events, not a mock-up.

const KIND_STYLE = {
  context: { color: "var(--faint)", icon: "○" },
  transaction: { color: "var(--accent)", icon: "◆" },
  queue: { color: "var(--faint)", icon: "▸" },
  agent: { color: "var(--muted)", icon: "●" },
  ready: { color: "var(--faint)", icon: "▸" },
  officer: { color: "var(--ok)", icon: "◈" },
  senior: { color: "#8b5cf6", icon: "◈" },
  escalation: { color: "var(--med)", icon: "▲" },
};

const SEV_COLOR = { HIGH: "var(--high)", MEDIUM: "var(--med)", LOW: "var(--ok)", NONE: "var(--faint)" };

function severityIn(text) {
  const m = text.match(/\b(HIGH|MEDIUM|LOW|NONE)\b/);
  return m ? m[1] : null;
}

function classify(entry) {
  const a = entry.action;
  if (entry.actor === "human") {
    return a.toLowerCase().includes("senior compliance officer") ? "senior" : "officer";
  }
  if (a.startsWith("Case assigned to")) return "escalation";
  if (a.startsWith("Transaction") && a.includes("received into")) return "queue";
  if (a.startsWith("Case ready")) return "ready";
  return "agent";
}

function buildEvents(caseData, customer, audit) {
  const events = [];
  if (customer?.onboarded) {
    events.push({ ts: customer.onboarded, kind: "context",
      title: "Customer onboarded", detail: customer.name });
  }
  if (caseData.transaction?.beneficiary_registered) {
    events.push({ ts: caseData.transaction.beneficiary_registered, kind: "context",
      title: "Beneficiary entity registered", detail: caseData.transaction.beneficiary_id });
  }
  if (caseData.transaction?.timestamp) {
    events.push({ ts: caseData.transaction.timestamp, kind: "transaction",
      title: "Transaction executed",
      detail: `₹${caseData.transaction.amount.toLocaleString("en-IN")} · ${caseData.transaction.route.join(" → ")}` });
  }
  for (const entry of audit) {
    events.push({ ts: entry.ts, kind: classify(entry), title: entry.action, detail: null, severity: severityIn(entry.action) });
  }
  return events.sort((a, b) => new Date(a.ts) - new Date(b.ts));
}

export default function InvestigationTimeline({ caseData, customer, audit }) {
  const events = React.useMemo(() => buildEvents(caseData, customer, audit), [caseData, customer, audit]);
  if (events.length === 0) return null;

  return (
    <div style={{ maxHeight: 280, overflowY: "auto", paddingRight: 4 }}>
      {events.map((e, i) => {
        const style = KIND_STYLE[e.kind] || KIND_STYLE.agent;
        const dotColor = e.severity ? SEV_COLOR[e.severity] : style.color;
        return (
          <div key={i} style={{ display: "flex", gap: 12 }}>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", flexShrink: 0 }}>
              <div style={{ width: 8, height: 8, borderRadius: 4, background: dotColor, marginTop: 5, flexShrink: 0 }} />
              {i < events.length - 1 && <div style={{ flex: 1, width: 1.5, background: "var(--border)", minHeight: 18, marginTop: 2 }} />}
            </div>
            <div style={{ paddingBottom: 12, minWidth: 0 }}>
              <div className="mono" style={{ fontSize: 9.5, color: "var(--faint)" }}>{formatWhen(e.ts)}</div>
              <div style={{ fontSize: 12, color: "var(--text)", lineHeight: 1.4 }}>{e.title}</div>
              {e.detail && <div style={{ fontSize: 11, color: "var(--muted)" }}>{e.detail}</div>}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function formatWhen(ts) {
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return ts;
  const hasTime = typeof ts === "string" && ts.includes("T");
  return hasTime
    ? d.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })
    : d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}
