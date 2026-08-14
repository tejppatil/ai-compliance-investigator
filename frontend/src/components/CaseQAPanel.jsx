import React from "react";
import { Card, Eyebrow } from "../components.jsx";
import { api } from "../api.js";

// A convenience layer over the evidence, NOT a replacement for it. The
// timeline, evidence list and graph remain the source of truth; this just
// lets an officer interrogate them in one place. Every answer is labelled
// AI-generated, and when the local model isn't running this says so plainly
// rather than producing a templated non-answer.

const SUGGESTED = [
  "Why is this case at its current risk band?",
  "What relationships exist between the parties?",
  "What do we still not know?",
];

export default function CaseQAPanel({ caseId }) {
  const [turns, setTurns] = React.useState([]);
  const [question, setQuestion] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const endRef = React.useRef(null);

  React.useEffect(() => { setTurns([]); setQuestion(""); }, [caseId]);
  React.useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }); }, [turns, busy]);

  async function ask(q) {
    const text = (q ?? question).trim();
    if (!text || busy) return;
    setQuestion("");
    setTurns((t) => [...t, { role: "officer", text }]);
    setBusy(true);
    try {
      const r = await api.askCase(caseId, text);
      setTurns((t) => [...t, {
        role: "ai",
        text: r.available ? r.answer : r.reason,
        unavailable: !r.available,
        grounded: r.grounded,
        evidenceIds: r.evidence_ids || [],
      }]);
    } catch (e) {
      setTurns((t) => [...t, { role: "ai", text: e.message, unavailable: true }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card style={{ marginTop: 16 }}>
      <Eyebrow right={<span className="mono" style={{ fontSize: 9, color: "var(--faint)" }}>EVIDENCE-SCOPED</span>}>
        Ask this case
      </Eyebrow>
      <div style={{ fontSize: 11.5, color: "var(--muted)", lineHeight: 1.5, marginBottom: 10 }}>
        Answered only from this case's own evidence — not from other cases, and not from general
        knowledge about the parties involved.
      </div>

      {turns.length === 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 10 }}>
          {SUGGESTED.map((s) => (
            <button key={s} className="btn-ghost" onClick={() => ask(s)} disabled={busy}
              style={{ padding: "5px 10px", fontSize: 11 }}>
              {s}
            </button>
          ))}
        </div>
      )}

      <div style={{ maxHeight: 320, overflowY: "auto", marginBottom: 10 }}>
        {turns.map((t, i) => (
          <div key={i} style={{ marginBottom: 10 }}>
            {t.role === "officer" ? (
              <div style={{ display: "flex", justifyContent: "flex-end" }}>
                <div style={{ maxWidth: "85%", background: "var(--raised)", border: "1px solid var(--border)",
                  borderRadius: "10px 10px 2px 10px", padding: "8px 11px", fontSize: 12.5, color: "var(--text)" }}>
                  {t.text}
                </div>
              </div>
            ) : (
              <div>
                <div className="mono" style={{ fontSize: 9, color: t.unavailable ? "var(--med)" : "var(--accent)",
                  marginBottom: 3, letterSpacing: ".05em" }}>
                  {t.unavailable ? "⚠ NOT AVAILABLE" : "◆ AI-GENERATED FROM CASE EVIDENCE"}
                </div>
                <div style={{ background: t.unavailable ? "var(--med-soft)" : "var(--sunken)",
                  border: `1px solid ${t.unavailable ? "var(--med-line)" : "var(--border)"}`,
                  borderRadius: "10px 10px 10px 2px", padding: "9px 12px", fontSize: 12.5,
                  color: "var(--text)", lineHeight: 1.55 }}>
                  {t.text}
                  {t.evidenceIds?.length > 0 && (
                    <div className="mono" style={{ fontSize: 9.5, color: "var(--faint)", marginTop: 6 }}>
                      cites: {t.evidenceIds.join(", ")}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}
        {busy && (
          <div className="mono blink" style={{ fontSize: 11, color: "var(--accent)" }}>
            reading the evidence…
          </div>
        )}
        <div ref={endRef} />
      </div>

      <form onSubmit={(e) => { e.preventDefault(); ask(); }} style={{ display: "flex", gap: 8 }}>
        <input type="text" value={question} onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask about this case's evidence…" maxLength={500} disabled={busy}
          style={{ flex: 1 }} />
        <button type="submit" className="btn-primary" disabled={busy || !question.trim()}
          style={{ padding: "8px 14px", fontSize: 12 }}>
          Ask
        </button>
      </form>
      <div style={{ fontSize: 10, color: "var(--faint)", marginTop: 8, lineHeight: 1.5 }}>
        AI-generated. Not a decision, not legal advice, and not a substitute for reading the
        evidence above. Every question and answer is written to the case audit trail.
      </div>
    </Card>
  );
}
