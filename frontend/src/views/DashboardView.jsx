import React from "react";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { Card, Kpi, Pill, Eyebrow, useThemeColors } from "../components.jsx";
import { api } from "../api.js";

export default function DashboardView({ openCase }) {
  const colors = useThemeColors(["high", "med", "ok", "faint", "surface", "border"]);
  const RISK_COLORS = { high: colors.high, medium: colors.med, low: colors.ok, none: colors.faint };
  const [data, setData] = React.useState(null);
  const [status, setStatus] = React.useState(null);
  const [network, setNetwork] = React.useState(null);
  const [error, setError] = React.useState(null);

  const load = React.useCallback(() => {
    Promise.all([api.dashboard(), api.status(), api.networkInsights()])
      .then(([d, s, n]) => { setData(d); setStatus(s); setNetwork(n); })
      .catch((e) => setError(e.message));
  }, []);
  React.useEffect(() => { load(); const t = setInterval(load, 20000); return () => clearInterval(t); }, [load]);

  if (error) return <ErrorBanner message={error} />;
  if (!data) return <div style={{ color: "var(--muted)", fontSize: 13 }}>Loading dashboard…</div>;

  const riskData = ["high", "medium", "low", "none"]
    .map((k) => ({ key: k, value: data.risk_distribution[k] }))
    .filter((d) => d.value > 0);

  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 14, marginBottom: 20 }}>
        <Kpi label="Total transactions" value={data.total_transactions} />
        <Kpi label="Investigations run" value={data.total_investigations} />
        <Kpi label="High-priority open" value={data.high_priority_open} sev={data.high_priority_open > 0 ? "high" : undefined} />
        <Kpi label="Awaiting officer review" value={data.awaiting_human_review} sev={data.awaiting_human_review > 0 ? "medium" : undefined} />
        <Kpi label="Awaiting senior review" value={data.awaiting_senior_review} sev={data.awaiting_senior_review > 0 ? "medium" : undefined} />
        <Kpi label="Overdue escalations" value={data.overdue_escalations} sev={data.overdue_escalations > 0 ? "high" : undefined} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.3fr 1fr", gap: 16 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
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

          <Card>
            <Eyebrow right={<span className="mono" style={{ fontSize: 9.5, color: "var(--faint)" }}>LIVE · updates every 20s</span>}>Recent activity</Eyebrow>
            {(!data.recent_activity || data.recent_activity.length === 0) ? (
              <div style={{ fontSize: 12.5, color: "var(--muted)" }}>Nothing yet — run an investigation to see the pipeline work.</div>
            ) : (
              <div>
                {data.recent_activity.map((a, i) => (
                  <div key={i} style={{ display: "flex", gap: 9, padding: "5px 0", fontSize: 11.5, borderBottom: i < data.recent_activity.length - 1 ? "1px solid var(--hair)" : "none" }}>
                    <span className="mono" style={{ color: "var(--faint)", flexShrink: 0, width: 68 }}>{new Date(a.ts).toLocaleTimeString()}</span>
                    <span className="mono" style={{ color: a.actor === "human" ? "var(--ok)" : "var(--faint)", flexShrink: 0, width: 60 }}>{a.actor}</span>
                    <span style={{ color: "var(--muted)" }}>{a.action}</span>
                  </div>
                ))}
              </div>
            )}
          </Card>

          <Card>
            <Eyebrow>Network insights — entities shared across customers</Eyebrow>
            {(!network || network.length === 0) ? (
              <div style={{ fontSize: 12.5, color: "var(--muted)" }}>
                No entity appears across more than one customer's cases yet — investigate more transactions to populate this.
              </div>
            ) : (
              <div>
                {network.map((n) => (
                  <div key={n.entity_id} style={{ padding: "8px 0", borderBottom: "1px solid var(--hair)" }}>
                    <div style={{ fontSize: 12.5, fontWeight: 600 }}>{n.entity_label}
                      <span className="mono" style={{ fontSize: 10, color: "var(--faint)", marginLeft: 6 }}>{n.entity_id}</span>
                    </div>
                    <div style={{ fontSize: 11, color: "var(--muted)" }}>
                      Appears in {n.case_count} case(s) across {n.customer_count} different customers.
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Card>
            <Eyebrow>Risk distribution</Eyebrow>
            {riskData.length === 0 ? (
              <div style={{ fontSize: 12.5, color: "var(--muted)" }}>No investigations yet.</div>
            ) : (
              <div style={{ height: 200 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={riskData} dataKey="value" nameKey="key" cx="50%" cy="50%" innerRadius={45} outerRadius={75} paddingAngle={2}>
                      {riskData.map((d) => <Cell key={d.key} fill={RISK_COLORS[d.key]} />)}
                    </Pie>
                    <Tooltip contentStyle={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 8, fontSize: 12 }} />
                    <Legend iconType="circle" wrapperStyle={{ fontSize: 11 }} formatter={(v) => v.toUpperCase()} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}
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
