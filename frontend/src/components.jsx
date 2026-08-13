import React from "react";

const SEV_CLASS = { high: "pill-high", medium: "pill-med", low: "pill-ok", none: "pill-none" };
const SEV_LABEL = { high: "HIGH", medium: "MEDIUM", low: "LOW", none: "NONE" };
const SEV_SCORE = { high: 1.0, medium: 0.6, low: 0.25, none: 0.0 };

export function Pill({ sev, children }) {
  const s = (sev || "none").toLowerCase();
  return <span className={`pill ${SEV_CLASS[s] || "pill-none"}`}>{children || SEV_LABEL[s] || sev}</span>;
}

export function Card({ children, style }) {
  return <div className="card" style={style}>{children}</div>;
}

export function Eyebrow({ children, right }) {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
      <span className="eyebrow">{children}</span>
      {right}
    </div>
  );
}

export function Kpi({ label, value, sev }) {
  return (
    <Card>
      <div className="kpi-label" style={{ marginBottom: 8 }}>{label}</div>
      <div className="kpi-value" style={sev ? { color: `var(--${sev === "high" ? "high" : sev === "medium" ? "med" : sev === "low" ? "ok" : "text"})` } : undefined}>
        {value}
      </div>
    </Card>
  );
}

export function ThemeToggle() {
  const [theme, setTheme] = React.useState(() => localStorage.getItem("vigilo-theme") || "light");
  React.useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("vigilo-theme", theme);
  }, [theme]);
  return (
    <button className="btn-ghost" onClick={() => setTheme((t) => (t === "light" ? "dark" : "light"))} title="Toggle theme">
      {theme === "light" ? "☾" : "☀"}
    </button>
  );
}

export function Sidebar({ view, setView }) {
  const items = [
    { k: "dashboard", label: "Dashboard", icon: "▦" },
    { k: "queue", label: "Case queue", icon: "▣" },
    { k: "regs", label: "Regulatory KB", icon: "▤" },
    { k: "about", label: "About & guardrails", icon: "◈" },
  ];
  return (
    <div style={{ width: 216, background: "var(--surface)", borderRight: "1px solid var(--border)", display: "flex", flexDirection: "column", flexShrink: 0 }}>
      <div style={{ padding: "18px 16px", borderBottom: "1px solid var(--border)" }}>
        <div className="eyebrow" style={{ color: "var(--accent)", marginBottom: 4 }}>GIFT · IFSC</div>
        <div style={{ fontFamily: "var(--font-display)", fontSize: 15, fontWeight: 700, lineHeight: 1.25 }}>
          Compliance<br />Investigator
        </div>
      </div>
      <div style={{ padding: 10, flex: 1 }}>
        {items.map((it) => {
          const on = view === it.k;
          return (
            <button key={it.k} onClick={() => setView(it.k)} className="navbtn"
              style={{ width: "100%", textAlign: "left", display: "flex", alignItems: "center", gap: 10,
                padding: "9px 11px", marginBottom: 3, borderRadius: 7, border: "none", cursor: "pointer",
                background: on ? "var(--raised)" : "transparent", color: on ? "var(--text)" : "var(--muted)",
                fontFamily: "var(--font-body)", fontSize: 13, fontWeight: on ? 600 : 500 }}>
              <span style={{ color: on ? "var(--accent)" : "var(--faint)", fontSize: 13 }}>{it.icon}</span>{it.label}
            </button>
          );
        })}
      </div>
      <div style={{ padding: "12px 16px", borderTop: "1px solid var(--border)", fontSize: 10.5, color: "var(--faint)", lineHeight: 1.5 }}>
        <div style={{ color: "var(--ok)", fontFamily: "var(--font-mono)", fontSize: 10 }}>● SYNTHETIC / PROTOTYPE DATA</div>
        AI gathers evidence.<br />A human decides.
      </div>
    </div>
  );
}

export function TopBar({ title, subtitle }) {
  return (
    <div style={{ height: 56, borderBottom: "1px solid var(--border)", background: "var(--surface)",
      display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 22px", flexShrink: 0 }}>
      <div style={{ fontSize: 14, fontWeight: 600, fontFamily: "var(--font-display)" }}>{title}</div>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        {subtitle && <span className="mono" style={{ fontSize: 11, color: "var(--faint)" }}>{subtitle}</span>}
        <ThemeToggle />
        <div style={{ display: "flex", alignItems: "center", gap: 7, padding: "5px 11px", background: "var(--raised)", borderRadius: 20, border: "1px solid var(--border)" }}>
          <div style={{ width: 20, height: 20, borderRadius: 10, background: "var(--accent)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 10, fontWeight: 700, color: "#fff" }}>SC</div>
          <span style={{ fontSize: 11.5, color: "var(--muted)" }}>S. Compliance Officer</span>
        </div>
      </div>
    </div>
  );
}

export function RiskMeter({ risk }) {
  const sev = (risk.band || "none").toLowerCase();
  return (
    <div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 12, marginBottom: 14 }}>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 32, fontWeight: 700,
          color: sev === "high" ? "var(--high)" : sev === "medium" ? "var(--med)" : sev === "low" ? "var(--ok)" : "var(--faint)" }}>
          {(risk.band || "none").toUpperCase()}
        </div>
        <div className="mono" style={{ fontSize: 13, color: "var(--muted)" }}>score {risk.score.toFixed(2)}/1.00</div>
      </div>
      {risk.rows.map((r) => {
        const rsev = r.severity;
        const color = rsev === "high" ? "var(--high)" : rsev === "medium" ? "var(--med)" : rsev === "low" ? "var(--ok)" : "var(--faint)";
        return (
          <div key={r.key} style={{ marginBottom: 10 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
              <span style={{ fontSize: 12.5, color: "var(--muted)" }}>{r.label} <span className="mono" style={{ color: "var(--faint)", fontSize: 10 }}>· w{r.weight}</span></span>
              <span className="mono" style={{ fontSize: 10.5, color }}>{rsev.toUpperCase()}</span>
            </div>
            <div style={{ height: 6, background: "var(--raised)", borderRadius: 3, overflow: "hidden" }}>
              <div style={{ width: `${(SEV_SCORE[rsev] * 100).toFixed(0)}%`, height: "100%", background: color, opacity: 0.85 }} />
            </div>
            {r.source_refs && r.source_refs.length > 0 &&
              <div className="mono" style={{ fontSize: 9.5, color: "var(--faint)", marginTop: 3 }}>from: {r.source_refs.join(", ")}</div>}
          </div>
        );
      })}
      <div style={{ marginTop: 16, paddingTop: 14, borderTop: "1px solid var(--border)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
          <span className="mono" style={{ fontSize: 11, color: "var(--accent)", letterSpacing: ".05em" }}>CONFIDENCE {risk.confidence.toFixed(2)}</span>
          <span style={{ fontSize: 10.5, color: "var(--faint)" }}>evidence quality — not a fraud probability</span>
        </div>
        <div style={{ height: 6, background: "var(--raised)", borderRadius: 3, overflow: "hidden" }}>
          <div style={{ width: `${(risk.confidence * 100).toFixed(0)}%`, height: "100%", background: "var(--accent)" }} />
        </div>
      </div>
    </div>
  );
}

const AGENT_META = {
  transaction_intelligence: { n: "Transaction Intelligence", d: "Statistical behaviour vs the customer's own history" },
  entity_intelligence: { n: "Entity Intelligence", d: "Who is involved and how they connect" },
  compliance_intelligence: { n: "Compliance Intelligence · RAG", d: "Relevant controls, retrieved with provenance" },
  document_analysis: { n: "Document Analysis", d: "Invoice fields checked against the transaction" },
};

export function AgentResultCard({ result }) {
  const m = AGENT_META[result.agent] || { n: result.agent, d: "" };
  const dot = result.severity === "high" ? "var(--high)" : result.severity === "medium" ? "var(--med)" : result.severity === "low" ? "var(--ok)" : "var(--faint)";
  return (
    <div style={{ display: "flex", gap: 14 }}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
        <div style={{ width: 12, height: 12, borderRadius: 6, background: dot, border: `2px solid ${dot}`, marginTop: 4 }} />
        <div style={{ flex: 1, width: 2, background: "var(--border)", marginTop: 4 }} />
      </div>
      <div style={{ flex: 1, paddingBottom: 18 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <div style={{ fontSize: 13.5, fontWeight: 600 }}>{m.n}</div>
            <div style={{ fontSize: 11, color: "var(--faint)" }}>{m.d}</div>
          </div>
          <Pill sev={result.severity} />
        </div>
        <div style={{ marginTop: 10 }}>
          {result.signals && result.signals.length > 0 && result.signals.map((s, i) => (
            <div key={i} style={{ display: "flex", gap: 9, alignItems: "flex-start", marginBottom: 5 }}>
              <Pill sev={s.severity} />
              <div style={{ flex: 1 }}>
                <span className="mono" style={{ fontSize: 10.5 }}>{s.type}</span>
                {s.metric && <span className="mono" style={{ fontSize: 10.5, color: "var(--accent)" }}> · {s.metric}</span>}
                <div style={{ fontSize: 11.5, color: "var(--muted)", lineHeight: 1.45 }}>{s.explanation}</div>
              </div>
            </div>
          ))}
          {result.findings && result.findings.map((f) => (
            <div key={f.id} style={{ fontSize: 12, color: "var(--muted)", marginBottom: 5, lineHeight: 1.5 }}>
              <span className="mono" style={{ color: "var(--faint)" }}>conf {f.confidence?.toFixed?.(2)} · </span>{f.description}
            </div>
          ))}
          {result.regulatory && result.regulatory.map((r) => (
            <div key={r.id} style={{ marginBottom: 8, paddingLeft: 9, borderLeft: "2px solid var(--accent)" }}>
              <div style={{ fontSize: 12, color: "var(--text)" }}>{r.title}</div>
              <div className="mono" style={{ fontSize: 9.5, color: "var(--faint)" }}>{r.id} · {r.section} · {r.regulator}</div>
              <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 2 }}>{r.why}</div>
              {r.source_url && <a href={r.source_url} target="_blank" rel="noreferrer" style={{ fontSize: 10, color: "var(--accent)" }}>source ↗</a>}
            </div>
          ))}
          {result.unknowns && result.unknowns.length > 0 && (
            <div style={{ fontSize: 10.5, color: "var(--med)", marginTop: 4, fontStyle: "italic" }}>
              {result.unknowns.join(" ")}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export function EvidenceGraph({ graph }) {
  if (!graph || !graph.nodes || graph.nodes.length === 0) return null;
  const KIND_COLOR = { transaction: "var(--accent)", entity: "#38bdf8", person: "#a78bfa", document: "var(--med)" };
  // Simple radial-ish layout computed from the graph payload — no hardcoded
  // node positions, since the graph itself is real backend output.
  const others = graph.nodes.filter((n) => n.kind !== "transaction");
  // 3 per row keeps 132px-wide nodes from colliding; height grows with rows so
  // a case with many related entities stays readable instead of overlapping.
  const cols = Math.max(1, Math.min(3, others.length));
  const rowCount = Math.ceil(others.length / cols);
  const W = 620, H = 130 + rowCount * 90, cx = W / 2, cy = 46;
  const positions = {};
  graph.nodes.forEach((n) => {
    if (n.kind === "transaction") positions[n.id] = { x: cx, y: cy };
  });
  others.forEach((n, i) => {
    const row = Math.floor(i / cols), col = i % cols;
    const inRow = Math.min(cols, others.length - row * cols);
    positions[n.id] = { x: (W / (inRow + 1)) * (col + 1), y: 150 + row * 90 };
  });
  const hotEdges = new Set(graph.edges.filter((e) => e.hot).map((e) => `${e.src}|${e.tgt}`));

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: "auto", display: "block" }}>
      {graph.edges.map((e, i) => {
        const A = positions[e.src], B = positions[e.tgt];
        if (!A || !B) return null;
        const hot = hotEdges.has(`${e.src}|${e.tgt}`);
        const mx = (A.x + B.x) / 2, my = (A.y + B.y) / 2;
        return (
          <g key={i}>
            <line x1={A.x} y1={A.y} x2={B.x} y2={B.y}
              stroke={hot ? "var(--high)" : "var(--border)"} strokeWidth={hot ? 1.6 : 1.2}
              strokeDasharray={hot ? "4 3" : "0"} opacity={hot ? 0.9 : 0.7} />
            <text x={mx} y={my - 3} fill={hot ? "var(--high)" : "var(--faint)"} fontSize={8} textAnchor="middle" opacity={0.9}>{e.label}</text>
          </g>
        );
      })}
      {graph.nodes.map((n) => {
        const p = positions[n.id];
        if (!p) return null;
        const w = 132, h = 40;
        return (
          <g key={n.id}>
            <rect x={p.x - w / 2} y={p.y - h / 2} width={w} height={h} rx={8}
              fill="var(--sunken)" stroke={KIND_COLOR[n.kind] || "var(--border)"} strokeWidth={1.2} />
            <circle cx={p.x - w / 2 + 12} cy={p.y} r={3.5} fill={KIND_COLOR[n.kind] || "var(--faint)"} />
            <text x={p.x - w / 2 + 24} y={p.y - 2} fontSize={10.5} fontWeight={600} fill="var(--text)">
              {n.label.length > 17 ? n.label.slice(0, 16) + "…" : n.label}
            </text>
            <text x={p.x - w / 2 + 24} y={p.y + 11} fontSize={8.5} fill="var(--faint)">{n.kind}</text>
          </g>
        );
      })}
    </svg>
  );
}
