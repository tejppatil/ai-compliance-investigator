import React from "react";
import { Card, Pill } from "../components.jsx";
import { api } from "../api.js";
import { ErrorBanner } from "./DashboardView.jsx";

export default function EscalationQueueView({ openCase }) {
  const [rows, setRows] = React.useState(null);
  const [error, setError] = React.useState(null);

  const load = React.useCallback(() => {
    api.listEscalations().then(setRows).catch((e) => setError(e.message));
  }, []);
  React.useEffect(() => { load(); const t = setInterval(load, 15000); return () => clearInterval(t); }, [load]);

  if (error) return <ErrorBanner message={error} />;
  if (!rows) return <div style={{ color: "var(--muted)", fontSize: 13 }}>Loading escalation queue…</div>;

  return (
    <div>
      <p style={{ color: "var(--muted)", fontSize: 13, marginTop: 0, marginBottom: 18, maxWidth: 640, lineHeight: 1.55 }}>
        Cases a tier-1 officer escalated for independent review. Only the assigned Senior Compliance
        Officer can decide these — switch persona (top right) to act on one. Enforced by the API,
        not just this screen: a tier-1 attempt on any of these gets a real 403.
      </p>
      {rows.length === 0 ? (
        <Card>
          <div style={{ fontSize: 13, color: "var(--muted)", textAlign: "center", padding: "18px 0" }}>
            No cases currently escalated.
          </div>
        </Card>
      ) : (
        <Card style={{ padding: 0 }}>
          <div style={{ display: "grid", gridTemplateColumns: "120px 1fr 100px 1fr 140px 90px", padding: "11px 18px", borderBottom: "1px solid var(--border)" }}>
            {["Case", "Transaction", "Priority", "Assigned to", "SLA", ""].map((h) => (
              <div key={h} className="eyebrow">{h}</div>
            ))}
          </div>
          {rows.map((r, i) => (
            <div key={r.case_id} onClick={() => openCase(r.transaction_id)} className="clickable"
              style={{ display: "grid", gridTemplateColumns: "120px 1fr 100px 1fr 140px 90px", padding: "13px 18px", alignItems: "center",
                borderBottom: i < rows.length - 1 ? "1px solid var(--hair)" : "none", cursor: "pointer" }}>
              <div className="mono" style={{ fontSize: 12, color: "var(--accent)" }}>{r.case_id}</div>
              <div className="mono" style={{ fontSize: 12 }}>{r.transaction_id}</div>
              <div><Pill sev={r.priority} /></div>
              <div style={{ fontSize: 12 }}>{r.assigned_to}</div>
              <div className="mono" style={{ fontSize: 10.5, color: r.overdue ? "var(--crit)" : "var(--faint)" }}>
                {r.overdue ? "OVERDUE" : new Date(r.sla_due_at).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
              </div>
              <div style={{ textAlign: "right", color: "var(--accent)", fontSize: 12 }}>Review →</div>
            </div>
          ))}
        </Card>
      )}
    </div>
  );
}
