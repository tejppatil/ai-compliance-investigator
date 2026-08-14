import React from "react";
import { MODULES, PERSONAS, usePersona } from "./persona.jsx";

const SEV_CLASS = { high: "pill-high", medium: "pill-med", low: "pill-ok", none: "pill-none" };
const SEV_LABEL = { high: "HIGH", medium: "MEDIUM", low: "LOW", none: "NONE" };
const SEV_SCORE = { high: 1.0, medium: 0.6, low: 0.25, none: 0.0 };

export function Pill({ sev, children }) {
  const s = (sev || "none").toLowerCase();
  return <span className={`pill ${SEV_CLASS[s] || "pill-none"}`}>{children || SEV_LABEL[s] || sev}</span>;
}

// Recharts renders bars/slices via its own internal style resolution, which
// doesn't reliably repaint an SVG `fill="var(--x)"` the way plain hand-written
// SVG (e.g. EvidenceGraph below) does — bars silently paint with no visible
// fill. Resolving the custom property to its actual computed color string
// once (and again on theme toggle) sidesteps that without hardcoding colors
// that would go stale if the palette in theme.css changes.
export function useThemeColors(names) {
  const [colors, setColors] = React.useState({});
  React.useEffect(() => {
    const resolve = () => {
      const style = getComputedStyle(document.documentElement);
      setColors(Object.fromEntries(names.map((n) => [n, style.getPropertyValue(`--${n}`).trim()])));
    };
    resolve();
    const observer = new MutationObserver(resolve);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => observer.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [names.join(",")]);
  return colors;
}

export function Card({ children, style, className }) {
  return <div className={className ? `card ${className}` : "card"} style={style}>{children}</div>;
}

// Grows from 0 to its target width on mount instead of appearing already at
// full size — a CSS transition alone won't animate if the target width is
// present on the very first paint, so this renders at 0 first and applies
// the real width one tick later.
export function AnimatedBar({ pct, color, height = 6 }) {
  const [width, setWidth] = React.useState(0);
  React.useEffect(() => { const t = requestAnimationFrame(() => setWidth(pct)); return () => cancelAnimationFrame(t); }, [pct]);
  return (
    <div style={{ height, background: "var(--raised)", borderRadius: height / 2, overflow: "hidden" }}>
      <div style={{ width: `${width}%`, height: "100%", background: color, opacity: 0.85, transition: "width .7s cubic-bezier(.22,1,.36,1)" }} />
    </div>
  );
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

const COMPLIANCE_ITEMS = [
  { k: "dashboard", label: "Dashboard", icon: "▦" },
  { k: "queue", label: "Case queue", icon: "▣" },
  { k: "new-transaction", label: "New transaction", icon: "✚" },
  { k: "escalations", label: "Escalation queue", icon: "▲" },
  { k: "how-it-works", label: "How it works", icon: "➜" },
  { k: "rules", label: "Detection rules", icon: "☰" },
  { k: "regs", label: "Regulatory KB", icon: "▤" },
  { k: "about", label: "About & guardrails", icon: "◈" },
];

export const CYBER_ITEMS = [
  { k: "command", label: "Command Center", icon: "◉" },
  { k: "case-ops", label: "Case Ops", icon: "⇄" },
  { k: "feed", label: "Transaction Feed", icon: "▤" },
  { k: "heatmap", label: "Crime Heat Map", icon: "◎" },
  { k: "intel", label: "Intelligence Graph", icon: "◈" },
];

function SidebarShell({ view, setView, items, eyebrow, title, footer }) {
  return (
    <div style={{ width: 216, background: "var(--surface)", borderRight: "1px solid var(--border)", display: "flex", flexDirection: "column", flexShrink: 0 }}>
      <div style={{ padding: "18px 16px", borderBottom: "1px solid var(--border)" }}>
        <div className="eyebrow" style={{ color: "var(--accent)", marginBottom: 4 }}>{eyebrow}</div>
        <div style={{ fontFamily: "var(--font-display)", fontSize: 15, fontWeight: 700, lineHeight: 1.25 }}>{title}</div>
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
        {footer}
      </div>
    </div>
  );
}

export function Sidebar({ view, setView }) {
  return (
    <SidebarShell view={view} setView={setView} items={COMPLIANCE_ITEMS} eyebrow="GIFT · IFSC"
      title={<>Compliance<br />Investigator</>}
      footer={<>
        <div style={{ color: "var(--ok)", fontFamily: "var(--font-mono)", fontSize: 10 }}>● SYNTHETIC / PROTOTYPE DATA</div>
        AI gathers evidence.<br />A human decides.
      </>} />
  );
}

export function CyberSidebar({ view, setView }) {
  return (
    <SidebarShell view={view} setView={setView} items={CYBER_ITEMS} eyebrow="CYBER CRIME UNIT"
      title={<>Fraud & Cyber<br />Command</>}
      footer={<>
        <div style={{ color: "var(--ok)", fontFamily: "var(--font-mono)", fontSize: 10 }}>● SIMULATED LIVE FEED</div>
        Freeze actions are officer-<br />triggered, always logged.
      </>} />
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
        <PersonaSwitcher />
      </div>
    </div>
  );
}

const ROLE_BADGE = { officer: "OFFICER", senior: "SENIOR", nodal: "NODAL LEAD", io: "INVESTIGATION OFFICER", analyst: "ANALYST" };
const ROLE_AVATAR = { senior: "#8b5cf6", nodal: "#8b5cf6", io: "var(--accent)", analyst: "#0ea5e9", officer: "var(--accent)" };

function PersonaSwitcher() {
  const { persona, setPersonaId, logout } = usePersona();
  const [open, setOpen] = React.useState(false);
  const ref = React.useRef(null);
  React.useEffect(() => {
    const onClick = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);
  const grouped = Object.values(MODULES).map((m) => ({
    module: m, people: Object.values(PERSONAS).filter((p) => p.module === m.id),
  }));
  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button data-testid="persona-switcher" onClick={() => setOpen((o) => !o)}
        style={{ display: "flex", alignItems: "center", gap: 7, padding: "5px 10px 5px 5px", background: "var(--raised)",
          borderRadius: 20, border: "1px solid var(--border)", cursor: "pointer" }}>
        <div style={{ width: 22, height: 22, borderRadius: 11, background: ROLE_AVATAR[persona.role] || "var(--accent)",
          display: "flex", alignItems: "center", justifyContent: "center", fontSize: 10, fontWeight: 700, color: "#fff", flexShrink: 0 }}>
          {persona.initials}
        </div>
        <div style={{ textAlign: "left" }}>
          <div style={{ fontSize: 11, color: "var(--text)", fontWeight: 600, lineHeight: 1.2 }}>{persona.name}</div>
          <div className="mono" style={{ fontSize: 8.5, color: "var(--faint)", lineHeight: 1.2 }}>ACTING AS · {ROLE_BADGE[persona.role] || persona.role.toUpperCase()}</div>
        </div>
        <span style={{ color: "var(--faint)", fontSize: 9, marginLeft: 2 }}>▾</span>
      </button>
      {open && (
        <div style={{ position: "absolute", right: 0, top: 38, width: 268, background: "var(--surface)", border: "1px solid var(--border)",
          borderRadius: 10, boxShadow: "0 8px 24px rgba(0,0,0,.16)", padding: 6, zIndex: 300 }}>
          <div style={{ fontSize: 9.5, color: "var(--faint)", padding: "5px 8px 3px" }}>DEMO PERSONA SWITCHER — not a login</div>
          {grouped.map(({ module, people }) => (
            <div key={module.id}>
              <div className="mono" style={{ fontSize: 8.5, color: "var(--faint)", padding: "6px 8px 2px", textTransform: "uppercase", letterSpacing: ".06em" }}>
                {module.label}
              </div>
              {people.map((p) => (
                <button key={p.id} onClick={() => { setPersonaId(p.id); setOpen(false); }}
                  style={{ width: "100%", display: "flex", alignItems: "center", gap: 9, padding: "8px", borderRadius: 7, border: "none",
                    background: p.id === persona.id ? "var(--raised)" : "transparent", cursor: "pointer", textAlign: "left" }}>
                  <div style={{ width: 22, height: 22, borderRadius: 11, background: ROLE_AVATAR[p.role] || "var(--accent)",
                    display: "flex", alignItems: "center", justifyContent: "center", fontSize: 10, fontWeight: 700, color: "#fff", flexShrink: 0 }}>
                    {p.initials}
                  </div>
                  <div>
                    <div style={{ fontSize: 12, color: "var(--text)", fontWeight: 600 }}>{p.name}</div>
                    <div style={{ fontSize: 10, color: "var(--muted)" }}>{p.title}</div>
                  </div>
                </button>
              ))}
            </div>
          ))}
          <div style={{ fontSize: 9.5, color: "var(--faint)", padding: "6px 8px 6px", lineHeight: 1.4, borderTop: "1px solid var(--border)", marginTop: 4 }}>
            Switching module changes console. The compliance module's tier-2 control is enforced server-side — a tier-1 decision on an escalated case gets a real 403 regardless of what this claims.
          </div>
          <button onClick={() => { setOpen(false); logout(); }}
            style={{ width: "100%", textAlign: "left", padding: "8px", borderRadius: 7, border: "none",
              background: "transparent", cursor: "pointer", fontSize: 12, color: "var(--crit)", fontWeight: 600 }}>
            ↩ Log out
          </button>
        </div>
      )}
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
            <AnimatedBar pct={SEV_SCORE[rsev] * 100} color={color} />
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
        <AnimatedBar pct={risk.confidence * 100} color="var(--accent)" />
      </div>
    </div>
  );
}

const AGENT_META = {
  transaction_intelligence: { n: "Transaction Intelligence", d: "Statistical behaviour vs the customer's own history" },
  entity_intelligence: { n: "Entity Intelligence", d: "Who is involved and how they connect" },
  compliance_intelligence: { n: "Compliance Intelligence · RAG", d: "Relevant controls, retrieved with provenance" },
  document_analysis: { n: "Document Analysis", d: "Invoice fields checked against the transaction" },
  kyc_completeness: { n: "KYC Completeness", d: "Onboarding record consistency — a data-quality check, not a risk score" },
};

// Pipeline order the orchestrator always returns agent_results in
// (aci/orchestrator.py: [t, e, c, d, k]) — used to render "not revealed yet"
// placeholders during the staggered reveal in CaseView.
export const AGENT_ORDER = ["transaction_intelligence", "entity_intelligence", "compliance_intelligence", "document_analysis", "kyc_completeness"];

export function PendingAgentCard({ agentKey, active }) {
  const m = AGENT_META[agentKey] || { n: agentKey, d: "" };
  return (
    <div style={{ display: "flex", gap: 14 }}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
        <div className={active ? "pulse-dot" : undefined} style={{ width: 12, height: 12, borderRadius: 6,
          background: active ? "var(--accent)" : "var(--border)", border: `2px solid ${active ? "var(--accent)" : "var(--border)"}`, marginTop: 4 }} />
        <div style={{ flex: 1, width: 2, background: "var(--border)", marginTop: 4 }} />
      </div>
      <div style={{ flex: 1, paddingBottom: 18 }}>
        <div style={{ fontSize: 13.5, fontWeight: 600, color: active ? "var(--text)" : "var(--faint)" }}>{m.n}</div>
        <div className={active ? "mono blink" : "mono"} style={{ fontSize: 11, color: active ? "var(--accent)" : "var(--faint)", marginTop: 2 }}>
          {active ? "analysing…" : "queued"}
        </div>
      </div>
    </div>
  );
}

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
      {graph.nodes.map((n, i) => {
        const p = positions[n.id];
        if (!p) return null;
        const w = 132, h = 40;
        return (
          <g key={n.id} className="svg-node-in" style={{ animationDelay: `${i * 90}ms` }}>
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
