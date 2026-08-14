import React from "react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { Card, Eyebrow, useThemeColors } from "../components.jsx";
import { CyberPill } from "./shared.jsx";

// `transactions`/`connected` come from the shared live feed in
// CyberModuleShell — this view is a pure renderer over that stream, so the
// WebSocket only opens once for the whole cyber module, not per-page.
export default function TransactionFeedView({ transactions, connected }) {
  const colors = useThemeColors(["accent", "crit", "border", "faint", "text", "surface"]);
  const [filter, setFilter] = React.useState("all"); // all | flagged

  const rows = filter === "flagged" ? transactions.filter((t) => t.flagged) : transactions;

  // Velocity chart: transaction count per 10-second bucket over the last
  // ~3 minutes, split flagged vs clean — real data from the buffer, not a
  // canned sparkline.
  const chartData = React.useMemo(() => {
    const buckets = new Map();
    const now = Date.now();
    for (const t of transactions) {
      const age = now - new Date(t.ts).getTime();
      if (age > 3 * 60 * 1000) continue;
      const bucket = Math.floor(age / 10000) * 10; // seconds ago, rounded to 10s
      const entry = buckets.get(bucket) || { t: bucket, clean: 0, flagged: 0 };
      if (t.flagged) entry.flagged += 1; else entry.clean += 1;
      buckets.set(bucket, entry);
    }
    return Array.from(buckets.values()).sort((a, b) => b.t - a.t).map((b) => ({ ...b, label: `-${b.t}s` }));
  }, [transactions]);

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <p style={{ color: "var(--muted)", fontSize: 13, margin: 0, maxWidth: 620, lineHeight: 1.55 }}>
          Live bank-transfer stream with automated rule-engine flagging — velocity bursts, known mule
          accounts, layering depth, high-risk cash-out locations, and single-transfer value.
        </p>
        <span className="mono" style={{ fontSize: 11, color: connected ? "var(--ok)" : "var(--crit)" }}>
          {connected ? "● LIVE" : "○ RECONNECTING…"}
        </span>
      </div>

      <Card style={{ marginBottom: 16 }}>
        <Eyebrow>Transaction velocity — last 3 minutes</Eyebrow>
        <ResponsiveContainer width="100%" height={140}>
          <AreaChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke={colors.border} vertical={false} />
            <XAxis dataKey="label" tick={{ fontSize: 10, fill: colors.faint }} reversed />
            <YAxis tick={{ fontSize: 10, fill: colors.faint }} allowDecimals={false} width={24} />
            <Tooltip contentStyle={{ background: colors.surface, border: `1px solid ${colors.border}`, fontSize: 11 }} />
            <Area type="monotone" dataKey="clean" stackId="1" stroke={colors.accent} fill={colors.accent} fillOpacity={0.25} name="Clean" />
            <Area type="monotone" dataKey="flagged" stackId="1" stroke={colors.crit} fill={colors.crit} fillOpacity={0.45} name="Flagged" />
          </AreaChart>
        </ResponsiveContainer>
      </Card>

      <Card style={{ padding: 0 }}>
        <div style={{ padding: "14px 18px 10px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <Eyebrow>Live feed · {rows.length}</Eyebrow>
          <div style={{ display: "flex", gap: 6 }}>
            <button className={filter === "all" ? "btn-primary" : "btn-ghost"} style={{ padding: "5px 10px", fontSize: 11 }} onClick={() => setFilter("all")}>All</button>
            <button className={filter === "flagged" ? "btn-primary" : "btn-ghost"} style={{ padding: "5px 10px", fontSize: 11 }} onClick={() => setFilter("flagged")}>Flagged only</button>
          </div>
        </div>
        <div style={{ maxHeight: 480, overflowY: "auto" }}>
          <table>
            <thead><tr><th>Time</th><th>Route</th><th>Amount</th><th>Channel</th><th>City</th><th>Risk</th></tr></thead>
            <tbody>
              {rows.slice(0, 100).map((t) => (
                <tr key={t.tx_id} style={t.flagged ? { background: "var(--crit-soft)" } : undefined}>
                  <td className="mono" style={{ fontSize: 10.5, color: "var(--faint)" }}>{new Date(t.ts).toLocaleTimeString()}</td>
                  <td className="mono" style={{ fontSize: 11 }}>{t.source_account} → {t.destination_account}</td>
                  <td className="mono" style={{ fontSize: 11.5 }}>₹{t.amount.toLocaleString("en-IN")}</td>
                  <td style={{ fontSize: 11 }}>{t.channel}</td>
                  <td style={{ fontSize: 11 }}>{t.city}</td>
                  <td>
                    {t.flagged
                      ? <span title={t.flag_reasons.join(" ")}><CyberPill severity={t.risk_score >= 60 ? "critical" : t.risk_score >= 35 ? "high" : "medium"}>{t.risk_score}</CyberPill></span>
                      : <span className="mono" style={{ fontSize: 10.5, color: "var(--faint)" }}>—</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
