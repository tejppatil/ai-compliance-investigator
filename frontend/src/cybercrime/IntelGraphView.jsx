import React from "react";
import { Card, Eyebrow } from "../components.jsx";
import { api } from "../api.js";

// Node categories map to the three intelligence classes an investigator
// actually separates: who (suspect identifiers), what moved (financial),
// and where/when (spatial + reporting).
const CATEGORY = {
  phone_number: "suspect", social_media_handle: "suspect", imei: "suspect",
  bank_account: "financial", upi_id: "financial", crypto_wallet: "financial",
  ip_address: "spatial", cell_tower: "spatial", fir_report: "spatial",
};
const CAT_COLOR = { suspect: "#a78bfa", financial: "#38bdf8", spatial: "var(--med)" };
const CAT_LABEL = { suspect: "Suspect entity", financial: "Financial entity", spatial: "Spatial / digital" };
const TYPE_LABEL = {
  phone_number: "Phone number", social_media_handle: "Social media handle", imei: "IMEI",
  bank_account: "Bank account", upi_id: "UPI ID", crypto_wallet: "Crypto wallet",
  ip_address: "IP address", cell_tower: "Cell tower", fir_report: "FIR / news report",
};

export default function IntelGraphView({ caseId, setCaseId }) {
  const [cases, setCases] = React.useState(null);
  const [graph, setGraph] = React.useState(null);
  const [selected, setSelected] = React.useState(null);
  const [error, setError] = React.useState(null);

  React.useEffect(() => {
    api.cyberCases().then((c) => {
      setCases(c);
      if (!caseId && c.length) setCaseId(c[0].case_id);
    }).catch((e) => setError(e.message));
  }, [caseId, setCaseId]);

  React.useEffect(() => {
    if (!caseId) return;
    api.cyberGraph(caseId).then(setGraph).catch((e) => setError(e.message));
  }, [caseId]);

  // Deterministic radial layout — same approach as the compliance module's
  // EvidenceGraph: positions computed from the payload, never hardcoded, so
  // a different case's graph lays out correctly without edits here.
  const layout = React.useMemo(() => {
    if (!graph) return null;
    const groups = { suspect: [], financial: [], spatial: [] };
    for (const n of graph.nodes) groups[CATEGORY[n.type] || "spatial"].push(n);
    const W = 720, H = 420;
    const positions = {};
    const columns = [
      { key: "suspect", x: W * 0.16 },
      { key: "financial", x: W * 0.5 },
      { key: "spatial", x: W * 0.84 },
    ];
    for (const col of columns) {
      const items = groups[col.key];
      items.forEach((n, i) => {
        positions[n.id] = { x: col.x, y: (H / (items.length + 1)) * (i + 1) };
      });
    }
    return { W, H, positions };
  }, [graph]);

  if (error) return <div className="card" style={{ color: "var(--crit)", fontSize: 13 }}>{error}</div>;
  if (!cases || !graph || !layout) return <div style={{ color: "var(--muted)", fontSize: 13 }}>Loading intelligence graph…</div>;

  return (
    <div>
      <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 14 }}>
        <select value={caseId || ""} onChange={(e) => { setCaseId(e.target.value); setSelected(null); }}
          style={{ fontSize: 12.5, padding: "8px 10px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--sunken)", color: "var(--text)" }}>
          {cases.map((c) => <option key={c.case_id} value={c.case_id}>{c.case_id} — {c.title}</option>)}
        </select>
        {Object.entries(CAT_LABEL).map(([k, label]) => (
          <span key={k} style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: 11, color: "var(--muted)" }}>
            <span style={{ width: 9, height: 9, borderRadius: 5, background: CAT_COLOR[k] }} />{label}
          </span>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: selected ? "1fr 330px" : "1fr", gap: 14, alignItems: "start" }}>
        <Card style={{ padding: 10 }}>
          <svg viewBox={`0 0 ${layout.W} ${layout.H}`} style={{ width: "100%", height: "auto", display: "block" }}>
            {graph.edges.map((e, i) => {
              const a = layout.positions[e.src], b = layout.positions[e.tgt];
              if (!a || !b) return null;
              return (
                <g key={i}>
                  <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="var(--border)" strokeWidth={1.2} opacity={0.8} />
                  <text x={(a.x + b.x) / 2} y={(a.y + b.y) / 2 - 4} fontSize={8} fill="var(--faint)" textAnchor="middle">
                    {e.relationship_type.replace(/_/g, " ")}
                  </text>
                </g>
              );
            })}
            {graph.nodes.map((n, i) => {
              const p = layout.positions[n.id];
              if (!p) return null;
              const cat = CATEGORY[n.type] || "spatial";
              const on = selected?.id === n.id;
              return (
                <g key={n.id} className="svg-node-in" style={{ animationDelay: `${i * 60}ms`, cursor: "pointer" }}
                  onClick={() => setSelected(n)}>
                  <circle cx={p.x} cy={p.y} r={on ? 13 : 10} fill={CAT_COLOR[cat]} fillOpacity={on ? 1 : 0.75}
                    stroke={on ? "var(--text)" : CAT_COLOR[cat]} strokeWidth={on ? 2 : 1} />
                  <text x={p.x} y={p.y + 26} fontSize={9.5} fill="var(--text)" textAnchor="middle">
                    {n.label.length > 20 ? n.label.slice(0, 19) + "…" : n.label}
                  </text>
                  <text x={p.x} y={p.y + 37} fontSize={8} fill="var(--faint)" textAnchor="middle">
                    conf {n.confidence.toFixed(2)}
                  </text>
                </g>
              );
            })}
          </svg>
          <div style={{ fontSize: 10.5, color: "var(--faint)", padding: "6px 8px 2px" }}>
            Click any node for its intelligence detail. Confidence is shown on every node — these are
            leads with varying reliability, not established facts.
          </div>
        </Card>

        {selected && (
          <Card className="reveal-in">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
              <div>
                <div className="mono" style={{ fontSize: 9.5, color: "var(--faint)", textTransform: "uppercase" }}>
                  {TYPE_LABEL[selected.type] || selected.type}
                </div>
                <div style={{ fontSize: 14, fontWeight: 600 }}>{selected.label}</div>
              </div>
              <button className="btn-ghost" style={{ padding: "3px 8px", fontSize: 14, lineHeight: 1 }} onClick={() => setSelected(null)}>×</button>
            </div>

            <div style={{ marginBottom: 12 }}>
              <div className="mono" style={{ fontSize: 9.5, color: "var(--faint)", textTransform: "uppercase", marginBottom: 3 }}>Confidence</div>
              <div style={{ height: 6, background: "var(--raised)", borderRadius: 3, overflow: "hidden" }}>
                <div style={{ width: `${selected.confidence * 100}%`, height: "100%", background: "var(--accent)" }} />
              </div>
              <div style={{ fontSize: 10.5, color: "var(--muted)", marginTop: 3 }}>
                {selected.confidence.toFixed(2)} — {selected.confidence >= 0.9 ? "corroborated by record" : selected.confidence >= 0.7 ? "strong indicator" : "unverified lead"}
              </div>
            </div>

            <div className="mono" style={{ fontSize: 9.5, color: "var(--faint)", textTransform: "uppercase", marginBottom: 5 }}>Raw indicators</div>
            {Object.entries(selected.details).map(([k, v]) => (
              <div key={k} style={{ display: "flex", justifyContent: "space-between", gap: 10, padding: "4px 0", borderBottom: "1px solid var(--hair)", fontSize: 11.5 }}>
                <span style={{ color: "var(--muted)" }}>{k.replace(/_/g, " ")}</span>
                <span style={{ color: "var(--text)", textAlign: "right" }}>{String(v)}</span>
              </div>
            ))}

            <div className="mono" style={{ fontSize: 9.5, color: "var(--faint)", textTransform: "uppercase", margin: "12px 0 5px" }}>Connections</div>
            {graph.edges.filter((e) => e.src === selected.id || e.tgt === selected.id).map((e, i) => {
              const otherId = e.src === selected.id ? e.tgt : e.src;
              const other = graph.nodes.find((n) => n.id === otherId);
              return (
                <div key={i} style={{ fontSize: 11.5, color: "var(--muted)", padding: "3px 0" }}>
                  {e.relationship_type.replace(/_/g, " ")} → <b style={{ color: "var(--text)" }}>{other?.label || otherId}</b>
                  <span className="mono" style={{ fontSize: 9.5, color: "var(--faint)" }}> ({e.confidence.toFixed(2)})</span>
                </div>
              );
            })}

            <div style={{ fontSize: 10, color: "var(--faint)", marginTop: 12, lineHeight: 1.5, borderTop: "1px solid var(--border)", paddingTop: 8 }}>
              Related case: <span className="mono" style={{ color: "var(--accent)" }}>{caseId}</span>. Synthetic OSINT
              indicators — no real person, account, or device is represented.
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
