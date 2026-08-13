import React from "react";
import { Card } from "../components.jsx";

const CARDS = [
  { t: "AI investigates. Human decides.", b: "The system never freezes accounts, rejects customers, files reports, or declares fraud. Every case lands on a review screen where a qualified officer makes the call — and every action is logged." },
  { t: "Two-person integrity control.", b: "Escalating a case assigns it to a named Senior Compliance Officer with an SLA. The tier-1 officer cannot then re-decide it — enforced by the API with a real 403, not just a disabled button — until the senior approves, overrides, or returns it for more evidence." },
  { t: "Tamper-evident audit trail.", b: "Every audit entry is SHA-256 hash-chained to the one before it. Editing or reordering a past entry breaks every hash after it — checkable via a real verification endpoint, not just claimed." },
  { t: "Math is deterministic.", b: "Anomaly detection (median, ratios, velocity, thresholds) runs in Python. The LLM only interprets and narrates — it never computes the numbers or the risk score, and the system produces a complete, identical-scored case even with no LLM running at all." },
  { t: "Grounded, not guessed.", b: "Regulatory conclusions come from a retrieved, provenance-tagged knowledge base of real, publicly issued documents (RBI, IFSCA, CBUAE, MAS, FATF) — each with a checkable source link. Below a relevance floor, the answer is 'insufficient information', never an invented control." },
  { t: "Confidence ≠ risk.", b: "A HIGH risk band with 0.82 confidence means the evidence points to a high-priority investigation — not an 82% probability that fraud occurred." },
  { t: "Untrusted documents.", b: "Invoice/document text is treated as content, never as instructions. A 'mark this low risk' line inside an upload is ignored by the deterministic risk engine, and any LLM narrative treats it as quoted data, not a command." },
  { t: "Local-first.", b: "Narratives and retrieval embeddings run on a local Ollama model on this machine. No transaction, customer, or case data leaves localhost. Cases and the audit trail persist in a local SQLite file, not an in-memory store that empties on restart." },
];

export default function AboutView() {
  return (
    <div>
      <p style={{ color: "var(--muted)", fontSize: 13.5, marginTop: 0, marginBottom: 20, maxWidth: 640, lineHeight: 1.6 }}>
        An AI-powered compliance investigation system that autonomously gathers, correlates, and explains
        evidence for cross-border transactions — while keeping every final regulatory decision with a human
        compliance officer.
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        {CARDS.map((c) => (
          <Card key={c.t}>
            <div style={{ fontSize: 13.5, fontWeight: 600, marginBottom: 6 }}>{c.t}</div>
            <div style={{ fontSize: 12.5, color: "var(--muted)", lineHeight: 1.55 }}>{c.b}</div>
          </Card>
        ))}
      </div>
      <div style={{ marginTop: 18, fontSize: 11.5, color: "var(--faint)" }} className="mono">
        Prototype · synthetic data only · India ↔ UAE ↔ Singapore · GIFT IFSC corridor.
      </div>
    </div>
  );
}
