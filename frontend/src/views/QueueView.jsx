import React from "react";
import { Card, Pill } from "../components.jsx";
import { api, caseIdFor } from "../api.js";
import { ErrorBanner } from "./DashboardView.jsx";

export default function QueueView({ openCase }) {
  const [txns, setTxns] = React.useState(null);
  const [cases, setCases] = React.useState({});
  const [error, setError] = React.useState(null);

  React.useEffect(() => {
    Promise.all([api.listTransactions(), api.listInvestigations()])
      .then(([t, inv]) => {
        setTxns(t);
        setCases(Object.fromEntries(inv.map((c) => [c.transaction_id, c])));
      })
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <ErrorBanner message={error} />;
  if (!txns) return <div style={{ color: "var(--muted)", fontSize: 13 }}>Loading queue…</div>;

  return (
    <div>
      <p style={{ color: "var(--muted)", fontSize: 13, marginTop: 0, marginBottom: 18, maxWidth: 620, lineHeight: 1.55 }}>
        Alerts arrive here from transaction monitoring. Open a case to run the multi-agent investigation —
        the system gathers and correlates evidence, then hands a structured, explainable case to you for the decision.
      </p>
      <Card style={{ padding: 0 }}>
        <div style={{ display: "grid", gridTemplateColumns: "130px 1fr 140px 130px 90px", padding: "11px 18px", borderBottom: "1px solid var(--border)" }}>
          <div className="eyebrow">Txn</div><div className="eyebrow">Customer · route</div>
          <div className="eyebrow">Amount</div><div className="eyebrow">Priority</div><div />
        </div>
        {txns.map((t, i) => {
          const c = cases[t.transaction_id];
          return (
            <div key={t.transaction_id} onClick={() => openCase(t.transaction_id)} className="clickable"
              style={{ display: "grid", gridTemplateColumns: "130px 1fr 140px 130px 90px", padding: "14px 18px", alignItems: "center",
                borderBottom: i < txns.length - 1 ? "1px solid var(--hair)" : "none", cursor: "pointer" }}>
              <div className="mono" style={{ fontSize: 12.5, color: "var(--accent)" }}>{t.transaction_id}</div>
              <div>
                <div style={{ fontSize: 13, fontWeight: 500 }}>{t.customer}</div>
                <div className="mono" style={{ fontSize: 10.5, color: "var(--faint)" }}>{t.route.join(" → ")} · {t.purpose}</div>
              </div>
              <div className="mono" style={{ fontSize: 12.5 }}>₹{t.amount.toLocaleString("en-IN")}</div>
              <div>{c ? <Pill sev={c.priority} /> : <span style={{ fontSize: 11, color: "var(--faint)" }}>Not yet investigated</span>}</div>
              <div style={{ textAlign: "right", color: "var(--accent)", fontSize: 12 }}>{c ? "Open →" : "Investigate →"}</div>
            </div>
          );
        })}
      </Card>
    </div>
  );
}
