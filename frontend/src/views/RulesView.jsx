import React from "react";
import { Card } from "../components.jsx";
import { api } from "../api.js";
import { ErrorBanner } from "./DashboardView.jsx";

const CATEGORY_COLOR = {
  behavioural: "var(--accent)", relationship: "#38bdf8", documentation: "var(--med)",
  customer: "#8b5cf6", geography: "var(--ok)", kyc: "var(--high)",
};

export default function RulesView() {
  const [rules, setRules] = React.useState(null);
  const [error, setError] = React.useState(null);
  const [filter, setFilter] = React.useState("all");

  React.useEffect(() => { api.rules().then(setRules).catch((e) => setError(e.message)); }, []);

  if (error) return <ErrorBanner message={error} />;
  if (!rules) return <div style={{ color: "var(--muted)", fontSize: 13 }}>Loading…</div>;

  const categories = ["all", ...new Set(rules.map((r) => r.category))];
  const shown = filter === "all" ? rules : rules.filter((r) => r.category === filter);

  return (
    <div>
      <p style={{ color: "var(--muted)", fontSize: 13, marginTop: 0, marginBottom: 18, maxWidth: 680, lineHeight: 1.6 }}>
        Every deterministic rule this system actually runs, with its real threshold pulled live
        from <code className="mono">aci/config.py</code> — not a paraphrase that could drift from
        the code. Anomaly detection is pure Python; nothing here is decided by a model.
      </p>
      <div style={{ display: "flex", gap: 6, marginBottom: 14, flexWrap: "wrap" }}>
        {categories.map((c) => (
          <button key={c} onClick={() => setFilter(c)}
            style={{ padding: "5px 12px", borderRadius: 16, fontSize: 11.5, cursor: "pointer",
              border: `1px solid ${filter === c ? "var(--accent)" : "var(--border)"}`,
              background: filter === c ? "var(--sunken)" : "transparent",
              color: filter === c ? "var(--accent)" : "var(--muted)", textTransform: "capitalize" }}>
            {c}
          </button>
        ))}
      </div>
      <Card style={{ padding: 0 }}>
        {shown.map((r, i) => (
          <div key={r.key} style={{ display: "flex", gap: 12, padding: "13px 18px", alignItems: "flex-start",
            borderBottom: i < shown.length - 1 ? "1px solid var(--hair)" : "none" }}>
            <span className="pill" style={{ background: "var(--raised)", color: CATEGORY_COLOR[r.category] || "var(--muted)",
              border: `1px solid ${CATEGORY_COLOR[r.category] || "var(--border)"}`, flexShrink: 0, minWidth: 90, textAlign: "center" }}>
              {r.category}
            </span>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div className="mono" style={{ fontSize: 12, fontWeight: 600 }}>{r.key}</div>
              <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 3, lineHeight: 1.5 }}>{r.trigger}</div>
              <div className="mono" style={{ fontSize: 9.5, color: "var(--faint)", marginTop: 4 }}>{r.agent} · {r.file}</div>
            </div>
          </div>
        ))}
      </Card>
    </div>
  );
}
