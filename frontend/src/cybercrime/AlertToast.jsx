import React from "react";

// Fires a toast banner whenever the live feed produces a newly-flagged
// transaction. Watches `lastFlagged` (from useLiveFeed) by identity — a new
// object reference each tick — and queues one toast per flag.
//
// Bottom-right and hard-capped at MAX_VISIBLE: flags arrive faster than a
// comfortable read time, so an uncapped top-right stack walls off the right
// column (the Intelligence Graph's detail drawer sits exactly there) within
// seconds. Newest wins; older ones are dropped rather than queued, because
// a stale alert is worth less than an unobstructed screen.
// 2, not 3: at 980px viewport height a third toast reaches up into the
// right-hand rail on the heat map (the "Top hotspots" card) — measured, not
// guessed. Two keeps the alert visible without eating page content.
const MAX_VISIBLE = 2;
const DISMISS_MS = 5000;

export default function AlertToast({ lastFlagged }) {
  const [queue, setQueue] = React.useState([]);
  const seen = React.useRef(new Set());

  React.useEffect(() => {
    if (!lastFlagged || seen.current.has(lastFlagged.tx_id)) return;
    seen.current.add(lastFlagged.tx_id);
    setQueue((q) => [lastFlagged, ...q].slice(0, MAX_VISIBLE));
    const t = setTimeout(() => setQueue((q) => q.filter((x) => x.tx_id !== lastFlagged.tx_id)), DISMISS_MS);
    return () => clearTimeout(t);
  }, [lastFlagged]);

  if (queue.length === 0) return null;

  return (
    <div style={{ position: "fixed", bottom: 22, right: 22, zIndex: 200, display: "flex", flexDirection: "column", gap: 8, width: 330, pointerEvents: "none" }}>
      {queue.map((t) => (
        <div key={t.tx_id} className="reveal-in" style={{ background: "var(--crit-soft)", border: "1px solid var(--crit-line)",
          borderRadius: 10, padding: "12px 14px", boxShadow: "0 8px 24px rgba(0,0,0,.18)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
            <span className="mono" style={{ fontSize: 10.5, color: "var(--crit)", fontWeight: 700 }}>⚠ FLAGGED TRANSACTION</span>
            <span className="mono" style={{ fontSize: 9.5, color: "var(--crit)" }}>risk {t.risk_score}</span>
          </div>
          <div style={{ fontSize: 12, color: "var(--text)", marginBottom: 3 }}>
            ₹{t.amount.toLocaleString("en-IN")} · {t.source_account} → {t.destination_account}
          </div>
          <div style={{ fontSize: 10.5, color: "var(--crit)", lineHeight: 1.4 }}>{t.flag_reasons[0]}</div>
        </div>
      ))}
    </div>
  );
}
