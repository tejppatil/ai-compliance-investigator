import React from "react";
import { Card, Kpi, Pill, Eyebrow } from "../components.jsx";
import { api } from "../api.js";

export default function DashboardView({ openCase }) {
  const [data, setData] = React.useState(null);
  const [status, setStatus] = React.useState(null);
  const [error, setError] = React.useState(null);

  React.useEffect(() => {
    Promise.all([api.dashboard(), api.status()])
      .then(([d, s]) => { setData(d); setStatus(s); })
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <ErrorBanner message={error} />;
  if (!data) return <div style={{ color: "var(--muted)", fontSize: 13 }}>Loading dashboard…</div>;

  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 16, marginBottom: 20 }}>
        <Kpi label="Total transactions" value={data.total_transactions} />
        <Kpi label="Investigations run" value={data.total_investigations} />
        <Kpi label="High-priority open" value={data.high_priority_open} sev={data.high_priority_open > 0 ? "high" : undefined} />
        <Kpi label="Awaiting human review" value={data.awaiting_human_review} sev={data.awaiting_human_review > 0 ? "medium" : undefined} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.3fr 1fr", gap: 16 }}>
        <Card>
          <Eyebrow>Recent investigations</Eyebrow>
          {data.recent_investigations.length === 0 ? (
            <div style={{ fontSize: 12.5, color: "var(--muted)" }}>No investigations run yet — open the case queue to start one.</div>
          ) : (
            <table>
              <thead><tr><th>Case</th><th>Transaction</th><th>Priority</th><th>Status</th></tr></thead>
              <tbody>
                {data.recent_investigations.map((c) => (
                  <tr key={c.case_id} className="clickable" onClick={() => openCase(c.transaction_id)}>
                    <td className="mono">{c.case_id}</td>
                    <td className="mono">{c.transaction_id}</td>
                    <td><Pill sev={c.priority} /></td>
                    <td style={{ fontSize: 11.5, color: "var(--muted)" }}>{c.status.replace(/_/g, " ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>

        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Card>
            <Eyebrow>Risk distribution</Eyebrow>
            {["high", "medium", "low", "none"].map((k) => (
              <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", fontSize: 12.5 }}>
                <span style={{ color: "var(--muted)" }}><Pill sev={k} /></span>
                <span className="mono">{data.risk_distribution[k]}</span>
              </div>
            ))}
          </Card>
          <Card>
            <Eyebrow>Local model status</Eyebrow>
            <StatusRow label="Ollama reachable" ok={status?.ollama?.available} />
            <StatusRow label={`Narrative model (${status?.ollama?.llm_model})`} ok={status?.ollama?.llm_model_pulled} />
            <StatusRow label={`Embedding model (${status?.ollama?.embed_model})`} ok={status?.ollama?.embed_model_pulled} />
            <div style={{ fontSize: 10.5, color: "var(--faint)", marginTop: 8 }}>
              Without Ollama, narratives fall back to a deterministic template — risk scoring is identical either way.
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

function StatusRow({ label, ok }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", fontSize: 12 }}>
      <span style={{ color: "var(--muted)" }}>{label}</span>
      <span style={{ color: ok ? "var(--ok)" : "var(--faint)" }}>{ok ? "● online" : "○ offline"}</span>
    </div>
  );
}

export function ErrorBanner({ message }) {
  return (
    <div className="card" style={{ borderColor: "var(--crit-line)", background: "var(--crit-soft)", color: "var(--crit)", fontSize: 13 }}>
      Could not reach the backend API. Is it running? (<span className="mono">uvicorn aci.api.app:app --reload</span>)
      <div style={{ marginTop: 6, fontSize: 11.5, opacity: 0.85 }}>{message}</div>
    </div>
  );
}
