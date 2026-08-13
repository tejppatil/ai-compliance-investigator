import React from "react";

// Horizontal, wrapping sequence of connected stage nodes — the visual "proof"
// that an investigation moves from one stage to the next, rather than a
// single opaque score. Purely prop-driven so the same component serves both
// the live case view (driven by real reveal/escalation state) and the static
// "How it works" page (driven by a fixed informational stage list).
const STATUS_COLOR = { pending: "var(--border)", active: "var(--accent)", done: "var(--faint)" };
const SEV_COLOR = { high: "var(--high)", medium: "var(--med)", low: "var(--ok)", none: "var(--faint)" };

export default function PipelineFlow({ stages, dense = false }) {
  return (
    <div style={{ display: "flex", flexWrap: "wrap", alignItems: "stretch", gap: 0 }}>
      {stages.map((s, i) => {
        const color = s.status === "done" && s.severity ? (SEV_COLOR[s.severity] || SEV_COLOR.none)
          : STATUS_COLOR[s.status] || STATUS_COLOR.pending;
        return (
          <React.Fragment key={s.key}>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", width: dense ? 108 : 128, flexShrink: 0 }}>
              <div className={s.status === "active" ? "pulse-dot" : undefined}
                style={{ width: 12, height: 12, borderRadius: 6, background: color, border: `2px solid ${color}`, marginBottom: 6 }} />
              <div style={{ fontSize: dense ? 10.5 : 11.5, fontWeight: 600, textAlign: "center", lineHeight: 1.3,
                color: s.status === "pending" ? "var(--faint)" : "var(--text)" }}>
                {s.label}
              </div>
              {s.status === "active" && <div className="mono blink" style={{ fontSize: 9, color: "var(--accent)", marginTop: 2 }}>working…</div>}
              {s.status === "done" && s.severity && (
                <div className="mono" style={{ fontSize: 9, color, marginTop: 2, textTransform: "uppercase" }}>{s.severity}</div>
              )}
              {!dense && s.description && (
                <div style={{ fontSize: 9.5, color: "var(--faint)", textAlign: "center", marginTop: 4, lineHeight: 1.4 }}>{s.description}</div>
              )}
              {!dense && s.file && <div className="mono" style={{ fontSize: 8.5, color: "var(--faint)", marginTop: 3 }}>{s.file}</div>}
            </div>
            {i < stages.length - 1 && (
              <div style={{ display: "flex", alignItems: "center", color: "var(--border)", fontSize: 14, flexShrink: 0, alignSelf: "flex-start", marginTop: dense ? 2 : 3, width: 20, justifyContent: "center" }}>
                →
              </div>
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}
