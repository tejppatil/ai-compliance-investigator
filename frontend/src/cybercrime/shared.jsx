import React from "react";

// Cyber Crime severities are low/medium/high/critical (not the compliance
// module's high/medium/low/none) — a distinct small pill rather than
// overloading components.jsx's Pill with a second vocabulary.
const SEV_COLOR = { critical: "var(--crit)", high: "var(--high)", medium: "var(--med)", low: "var(--ok)" };
const SEV_BG = { critical: "var(--crit-soft)", high: "var(--high-soft)", medium: "var(--med-soft)", low: "var(--ok-soft)" };
const SEV_BORDER = { critical: "var(--crit-line)", high: "var(--high-line)", medium: "var(--med-line)", low: "var(--ok-line)" };

export function CyberPill({ severity, children }) {
  const s = (severity || "low").toLowerCase();
  return (
    <span className="pill" style={{ color: SEV_COLOR[s] || "var(--faint)", background: SEV_BG[s] || "var(--raised)",
      border: `1px solid ${SEV_BORDER[s] || "var(--border)"}` }}>
      {children || s.toUpperCase()}
    </span>
  );
}

const STATUS_COLOR = {
  "Active Investigation": "var(--accent)",
  "Cold Case": "var(--faint)",
  "Escalated to Nodal": "var(--med)",
  "Pending Freeze": "var(--crit)",
  "Available": "var(--ok)",
};

export function StatusDot({ status }) {
  const c = STATUS_COLOR[status] || "var(--faint)";
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
      <span style={{ width: 7, height: 7, borderRadius: 4, background: c, flexShrink: 0 }} />
      <span style={{ fontSize: 11.5, color: "var(--text)" }}>{status}</span>
    </span>
  );
}

export function timeAgo(iso) {
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return `${Math.floor(s)}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}
