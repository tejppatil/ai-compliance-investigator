import React from "react";
import { Card, Eyebrow, Pill } from "../components.jsx";
import { api } from "../api.js";
import { ErrorBanner } from "./DashboardView.jsx";

// Chip colours by reason code — a sanctions chip must not look like an
// age chip, since the whole point of showing reasons is that they aren't
// interchangeable.
const REASON_STYLE = {
  sanctions_hit: { fg: "var(--crit)", bg: "var(--crit-soft)", line: "var(--crit-line)" },
  sanctions_possible: { fg: "var(--med)", bg: "var(--med-soft)", line: "var(--med-line)" },
  sla_breached: { fg: "var(--crit)", bg: "var(--crit-soft)", line: "var(--crit-line)" },
  sla_imminent: { fg: "var(--med)", bg: "var(--med-soft)", line: "var(--med-line)" },
  risk_band: { fg: "var(--high)", bg: "var(--high-soft)", line: "var(--high-line)" },
  age: { fg: "var(--muted)", bg: "var(--raised)", line: "var(--border)" },
};

function ReasonChip({ reason }) {
  const s = REASON_STYLE[reason.code] || REASON_STYLE.age;
  return (
    <span title={`+${reason.points} priority`}
      style={{ fontSize: 10, fontFamily: "var(--font-mono)", padding: "2px 7px", borderRadius: 10,
        color: s.fg, background: s.bg, border: `1px solid ${s.line}`, whiteSpace: "nowrap" }}>
      {reason.label}
    </span>
  );
}

export default function QueueView({ openCase }) {
  const [queue, setQueue] = React.useState(null);
  const [model, setModel] = React.useState(null);
  const [txns, setTxns] = React.useState(null);
  const [showModel, setShowModel] = React.useState(false);
  const [error, setError] = React.useState(null);

  const load = React.useCallback(() => {
    Promise.all([api.queue(), api.listTransactions()])
      .then(([q, t]) => { setQueue(q.cases); setModel(q.model); setTxns(t); })
      .catch((e) => setError(e.message));
  }, []);
  React.useEffect(() => { load(); const t = setInterval(load, 20000); return () => clearInterval(t); }, [load]);

  if (error) return <ErrorBanner message={error} />;
  if (!queue || !txns) return <div style={{ color: "var(--muted)", fontSize: 13 }}>Loading queue…</div>;

  // Ranking can only speak to cases that have actually been analysed, so
  // uninvestigated transactions are listed separately rather than being
  // given an invented position in the priority order.
  const investigated = new Set(queue.map((c) => c.transaction_id));
  const pending = txns.filter((t) => !investigated.has(t.transaction_id));
  const txnById = Object.fromEntries(txns.map((t) => [t.transaction_id, t]));

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16, gap: 20 }}>
        <p style={{ color: "var(--muted)", fontSize: 13, margin: 0, maxWidth: 620, lineHeight: 1.55 }}>
          Ranked by triage priority, not arrival order — a sanctions match, a breached SLA, and a HIGH
          risk band are not equally urgent. Every case shows the reasons behind its position.
        </p>
        <button className="btn-ghost" style={{ padding: "6px 11px", fontSize: 11, flexShrink: 0 }}
          onClick={() => setShowModel((s) => !s)}>
          {showModel ? "Hide" : "How is this ordered?"}
        </button>
      </div>

      {showModel && model && (
        <Card style={{ marginBottom: 16 }}>
          <Eyebrow>Ranking model</Eyebrow>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 10 }}>
            {Object.entries(model.weights).map(([k, v]) => (
              <span key={k} className="mono" style={{ fontSize: 10.5, padding: "3px 8px", borderRadius: 6,
                background: "var(--sunken)", border: "1px solid var(--border)", color: "var(--muted)" }}>
                {k.replace(/_/g, " ")} · {v}
              </span>
            ))}
          </div>
          {model.notes.map((n, i) => (
            <div key={i} style={{ fontSize: 11.5, color: "var(--muted)", lineHeight: 1.55 }}>· {n}</div>
          ))}
        </Card>
      )}

      <Card style={{ padding: 0, marginBottom: 16 }}>
        <div style={{ padding: "14px 18px 6px" }}>
          <Eyebrow>Work queue · {queue.length}</Eyebrow>
        </div>
        {queue.length === 0 ? (
          <div style={{ padding: "6px 18px 18px", fontSize: 12.5, color: "var(--muted)" }}>
            Nothing outstanding — investigate a transaction below to populate the queue.
          </div>
        ) : queue.map((c, i) => {
          const t = txnById[c.transaction_id];
          return (
            <div key={c.case_id} onClick={() => openCase(c.transaction_id)} className="clickable"
              style={{ display: "grid", gridTemplateColumns: "40px 130px 1fr 120px 70px",
                padding: "13px 18px", alignItems: "center", cursor: "pointer",
                borderBottom: i < queue.length - 1 ? "1px solid var(--hair)" : "none" }}>
              <div className="mono" style={{ fontSize: 14, fontWeight: 700, color: "var(--faint)" }}>{c.queue_position}</div>
              <div>
                <div className="mono" style={{ fontSize: 12.5, color: "var(--accent)" }}>{c.transaction_id}</div>
                <div className="mono" style={{ fontSize: 9.5, color: "var(--faint)" }}>{c.case_id}</div>
              </div>
              <div>
                <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 4 }}>
                  {t ? t.customer : c.case_id}
                  {t && <span className="mono" style={{ fontSize: 10.5, color: "var(--faint)" }}> · {t.route.join(" → ")}</span>}
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
                  {c.triage_reasons.map((r) => <ReasonChip key={r.code} reason={r} />)}
                </div>
              </div>
              <div><Pill sev={c.priority} /></div>
              <div style={{ textAlign: "right", color: "var(--accent)", fontSize: 12 }}>Open →</div>
            </div>
          );
        })}
      </Card>

      {pending.length > 0 && (
        <Card style={{ padding: 0 }}>
          <div style={{ padding: "14px 18px 6px" }}>
            <Eyebrow>Not yet investigated · {pending.length}</Eyebrow>
            <div style={{ fontSize: 11.5, color: "var(--muted)", marginTop: -4, marginBottom: 6 }}>
              Unranked by design — priority can't be assessed before the case has been analysed.
            </div>
          </div>
          {pending.map((t, i) => (
            <div key={t.transaction_id} onClick={() => openCase(t.transaction_id)} className="clickable"
              style={{ display: "grid", gridTemplateColumns: "170px 1fr 140px 90px", padding: "13px 18px",
                alignItems: "center", cursor: "pointer",
                borderBottom: i < pending.length - 1 ? "1px solid var(--hair)" : "none" }}>
              <div className="mono" style={{ fontSize: 12.5, color: "var(--accent)" }}>{t.transaction_id}</div>
              <div>
                <div style={{ fontSize: 13, fontWeight: 500 }}>{t.customer}</div>
                <div className="mono" style={{ fontSize: 10.5, color: "var(--faint)" }}>{t.route.join(" → ")} · {t.purpose}</div>
              </div>
              <div className="mono" style={{ fontSize: 12.5 }}>₹{t.amount.toLocaleString("en-IN")}</div>
              <div style={{ textAlign: "right", color: "var(--accent)", fontSize: 12 }}>Investigate →</div>
            </div>
          ))}
        </Card>
      )}
    </div>
  );
}
