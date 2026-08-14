import React from "react";
import { Card, Eyebrow } from "../components.jsx";

// A sanctions hit is deliberately NOT rendered as one more line item among
// the agent findings: it's the single most consequential thing this system
// can surface, and burying it in a uniform list would understate it exactly
// the way a weighted risk dimension would have (see aci/agents/risk_agent.py
// on why screening is a floor, not a dimension). Hence a full-width banner
// with its own colour treatment.
//
// A CLEAR result still renders — quietly — because "screened, nothing found"
// is a positive assertion an auditor needs, not an absence worth hiding.

const STYLE = {
  hit: {
    bg: "var(--crit-soft)", line: "var(--crit-line)", fg: "var(--crit)",
    icon: "⛔", title: "SANCTIONS MATCH — CONFIRMED",
  },
  possible: {
    bg: "var(--med-soft)", line: "var(--med-line)", fg: "var(--med)",
    icon: "⚠", title: "POSSIBLE SANCTIONS MATCH — HUMAN CONFIRMATION REQUIRED",
  },
  clear: {
    bg: "var(--ok-soft)", line: "var(--ok-line)", fg: "var(--ok)",
    icon: "✓", title: "SANCTIONS SCREENING — NO MATCH",
  },
};

export default function SanctionsPanel({ result, status, floorReason }) {
  const [open, setOpen] = React.useState(false);
  if (!result) return null;
  const s = STYLE[status] || STYLE.clear;
  const extra = result.extra || {};
  const screened = extra.screened || [];

  return (
    <Card style={{ marginTop: 16, background: s.bg, borderColor: s.line }}>
      <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
        <div style={{ fontSize: 20, lineHeight: 1, color: s.fg, flexShrink: 0 }}>{s.icon}</div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="mono" style={{ fontSize: 11, fontWeight: 700, color: s.fg, letterSpacing: ".04em" }}>
            {s.title}
          </div>

          {result.findings.length > 0 ? (
            result.findings.map((f) => (
              <div key={f.id} style={{ fontSize: 12.5, color: "var(--text)", lineHeight: 1.55, marginTop: 6 }}>
                {f.description}
              </div>
            ))
          ) : (
            <div style={{ fontSize: 12.5, color: "var(--muted)", lineHeight: 1.55, marginTop: 4 }}>
              {screened.length} {screened.length === 1 ? "party" : "parties"} screened against{" "}
              {(extra.lists_screened || []).length} list(s) — no match at or above the{" "}
              {Math.round((extra.thresholds?.possible ?? 0) * 100)}% reporting threshold.
            </div>
          )}

          {floorReason && (
            <div style={{ fontSize: 11.5, color: s.fg, marginTop: 8, paddingTop: 8, borderTop: `1px solid ${s.line}` }}>
              <b>Risk band override:</b> {floorReason}
            </div>
          )}

          <button onClick={() => setOpen((o) => !o)} className="btn-ghost"
            style={{ marginTop: 10, padding: "4px 10px", fontSize: 11 }}>
            {open ? "Hide screening detail" : "Show screening detail"}
          </button>

          {open && (
            <div style={{ marginTop: 10, paddingTop: 10, borderTop: `1px solid ${s.line}` }}>
              <div className="mono" style={{ fontSize: 9.5, color: "var(--faint)", textTransform: "uppercase", marginBottom: 4 }}>
                Parties screened
              </div>
              {screened.map((p) => (
                <div key={p.name} style={{ display: "flex", justifyContent: "space-between", gap: 10,
                  fontSize: 11.5, padding: "3px 0", borderBottom: "1px solid var(--hair)" }}>
                  <span style={{ color: "var(--text)" }}>{p.name} <span style={{ color: "var(--faint)" }}>· {p.role}</span></span>
                  <span className="mono" style={{ color: p.hit ? s.fg : "var(--faint)", flexShrink: 0 }}>
                    {p.hit ? `${Math.round(p.score * 100)}% match` : "no match"}
                  </span>
                </div>
              ))}

              <div className="mono" style={{ fontSize: 9.5, color: "var(--faint)", textTransform: "uppercase", margin: "10px 0 4px" }}>
                Thresholds
              </div>
              <div style={{ fontSize: 11, color: "var(--muted)" }}>
                Confirmed ≥ {Math.round((extra.thresholds?.confirmed ?? 0) * 100)}% ·
                Possible ≥ {Math.round((extra.thresholds?.possible ?? 0) * 100)}% ·
                suffix-stripped token-sort similarity
              </div>

              {(extra.known_limitations || []).length > 0 && (
                <>
                  <div className="mono" style={{ fontSize: 9.5, color: "var(--faint)", textTransform: "uppercase", margin: "10px 0 4px" }}>
                    What this screening does NOT do
                  </div>
                  {extra.known_limitations.map((l, i) => (
                    <div key={i} style={{ fontSize: 11, color: "var(--muted)", lineHeight: 1.5 }}>· {l}</div>
                  ))}
                </>
              )}

              {extra.disclaimer && (
                <div style={{ fontSize: 10.5, color: "var(--faint)", marginTop: 10, lineHeight: 1.5 }}>
                  {extra.disclaimer}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}
