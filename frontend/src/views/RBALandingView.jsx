import React from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, ResponsiveContainer } from "recharts";
import { Card, Pill, ThemeToggle, useThemeColors } from "../components.jsx";
import { api } from "../api.js";
import { usePersona, PERSONAS } from "../persona.jsx";

const SEV_COLOR = { high: "var(--high)", medium: "var(--med)", low: "var(--ok)", none: "var(--faint)" };

export default function RBALandingView() {
  const { login } = usePersona();
  const colors = useThemeColors(["accent", "surface", "border", "text", "faint"]);
  const [methodology, setMethodology] = React.useState(null);
  const [fatfR1, setFatfR1] = React.useState(null);
  const [error, setError] = React.useState(null);
  const [name, setName] = React.useState("");
  const [role, setRole] = React.useState("officer");

  React.useEffect(() => {
    Promise.all([api.riskMethodology(), api.listRegulations()])
      .then(([m, regs]) => {
        setMethodology(m);
        setFatfR1(regs.find((r) => r.id === "FATF-R1") || null);
      })
      .catch((e) => setError(e.message));
  }, []);

  function submit(e) {
    e.preventDefault();
    login(name, role);
  }

  return (
    <div style={{ minHeight: "100vh", background: "var(--page)", overflowY: "auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "18px 32px", borderBottom: "1px solid var(--border)" }}>
        <div>
          <div className="eyebrow" style={{ color: "var(--accent)", marginBottom: 2 }}>GIFT · IFSC</div>
          <div style={{ fontFamily: "var(--font-display)", fontSize: 17, fontWeight: 700 }}>AI Compliance Investigator</div>
        </div>
        <ThemeToggle />
      </div>

      <div style={{ maxWidth: 920, margin: "0 auto", padding: "40px 24px 60px" }}>
        <div style={{ textAlign: "center", marginBottom: 40 }}>
          <div className="eyebrow" style={{ color: "var(--accent)", marginBottom: 10 }}>RISK-BASED APPROACH</div>
          <h1 style={{ fontFamily: "var(--font-display)", fontSize: 32, fontWeight: 700, margin: "0 0 14px", lineHeight: 1.2 }}>
            Risk isn't one number from nowhere.
          </h1>
          <p style={{ fontSize: 14.5, color: "var(--muted)", maxWidth: 620, margin: "0 auto", lineHeight: 1.6 }}>
            This system implements a Risk-Based Approach per FATF Recommendation 1 — six weighted
            dimensions, each traceable to concrete evidence, combined into one explainable score.
            A customer's own risk rating can drive a case to review even when the transaction
            itself looks unremarkable.
          </p>
        </div>

        {error && <div className="card" style={{ borderColor: "var(--crit-line)", color: "var(--crit)", marginBottom: 24 }}>{error}</div>}

        {methodology && (
          <>
            <Card style={{ marginBottom: 20 }}>
              <div className="eyebrow" style={{ marginBottom: 14 }}>The six dimensions</div>
              <div style={{ height: 220 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={methodology.dimensions} layout="vertical" margin={{ left: 8, right: 24 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
                    <XAxis type="number" domain={[0, 0.4]} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
                      tick={{ fill: colors.faint, fontSize: 10 }} axisLine={{ stroke: colors.border }} />
                    <YAxis type="category" dataKey="label" width={150} tick={{ fill: colors.text, fontSize: 11 }} axisLine={{ stroke: colors.border }} />
                    <Tooltip
                      contentStyle={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 8, fontSize: 12 }}
                      formatter={(v) => [`${(v * 100).toFixed(0)}% weight`, ""]} labelStyle={{ color: colors.text }} />
                    <Bar dataKey="weight" radius={[0, 4, 4, 0]}>
                      {methodology.dimensions.map((d) => <Cell key={d.key} fill={colors.accent} fillOpacity={d.key === "customer_risk" ? 1 : 0.55} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginTop: 12 }}>
                {methodology.dimensions.map((d) => (
                  <div key={d.key} style={{ padding: 10, background: "var(--sunken)", borderRadius: 8 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12.5, fontWeight: 600 }}>
                      <span>{d.label}</span><span className="mono" style={{ color: "var(--accent)" }}>{(d.weight * 100).toFixed(0)}%</span>
                    </div>
                    <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 3, lineHeight: 1.5 }}>{d.description}</div>
                  </div>
                ))}
              </div>
            </Card>

            <Card style={{ marginBottom: 20 }}>
              <div className="eyebrow" style={{ marginBottom: 12 }}>Recommended action by risk band</div>
              <table>
                <thead><tr><th>Band</th><th>Recommended action</th></tr></thead>
                <tbody>
                  {Object.entries(methodology.risk_policy).map(([band, action]) => (
                    <tr key={band}><td><Pill sev={band} /></td><td style={{ fontSize: 12.5, color: "var(--muted)" }}>{action}</td></tr>
                  ))}
                </tbody>
              </table>
              <div style={{ fontSize: 10.5, color: "var(--faint)", marginTop: 10, lineHeight: 1.5 }}>
                Recommendations for the human reviewer — never an automated action. The system never
                freezes, blocks, or closes anything on its own.
              </div>
            </Card>

            {fatfR1 && (
              <Card style={{ marginBottom: 20 }}>
                <div className="eyebrow" style={{ marginBottom: 8 }}>Grounded in a real citation</div>
                <div style={{ fontSize: 13.5, fontWeight: 600 }}>{fatfR1.title}</div>
                <div className="mono" style={{ fontSize: 10, color: "var(--faint)", margin: "4px 0 8px" }}>
                  {fatfR1.id} · {fatfR1.section} · {fatfR1.regulator}
                </div>
                <div style={{ fontSize: 12.5, color: "var(--muted)", lineHeight: 1.55 }}>{fatfR1.summary}</div>
                {fatfR1.source_url && <a href={fatfR1.source_url} target="_blank" rel="noreferrer" style={{ fontSize: 11, color: "var(--accent)", marginTop: 8, display: "inline-block" }}>source ↗</a>}
              </Card>
            )}

            <Card style={{ marginBottom: 40 }}>
              <div className="eyebrow" style={{ marginBottom: 8 }}>Seen in isolation</div>
              <p style={{ fontSize: 12.5, color: "var(--muted)", lineHeight: 1.6, margin: 0 }}>
                Transaction <b style={{ color: "var(--text)" }}>TX-31204</b> in the demo queue has zero
                behavioural anomalies — the amount is close to baseline, the counterparty is
                long-established, the invoice is well-documented. It still reaches review, because the
                customer alone carries a HIGH persistent risk rating. Sign in below and open it to see
                the customer-risk row drive the case on its own.
              </p>
            </Card>
          </>
        )}

        <Card style={{ maxWidth: 420, margin: "0 auto" }}>
          <div className="eyebrow" style={{ marginBottom: 4, textAlign: "center" }}>SIGN IN</div>
          <div style={{ fontSize: 13, fontWeight: 600, textAlign: "center", marginBottom: 18 }}>
            Enter the compliance console
          </div>
          <form onSubmit={submit}>
            <label style={{ fontSize: 11, color: "var(--muted)", display: "block", marginBottom: 4 }}>Name</label>
            <input type="text" value={name} onChange={(e) => setName(e.target.value)}
              placeholder={PERSONAS[role].name} style={{ width: "100%", marginBottom: 14 }} />
            <label style={{ fontSize: 11, color: "var(--muted)", display: "block", marginBottom: 4 }}>Role</label>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 18 }}>
              {Object.values(PERSONAS).map((p) => (
                <button key={p.id} type="button" onClick={() => setRole(p.id)}
                  style={{ padding: "10px 8px", borderRadius: 8, cursor: "pointer", textAlign: "left",
                    border: `1.5px solid ${role === p.id ? "var(--accent)" : "var(--border)"}`,
                    background: role === p.id ? "var(--sunken)" : "transparent" }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text)" }}>{p.title}</div>
                </button>
              ))}
            </div>
            <button type="submit" className="btn-primary" style={{ width: "100%" }}>Sign in</button>
          </form>
          <div style={{ fontSize: 10, color: "var(--faint)", marginTop: 14, lineHeight: 1.5, textAlign: "center" }}>
            Demo sign-in for this console — no password required. The two-tier escalation control
            this unlocks is enforced by the API itself (a real 403), not by this screen.
          </div>
        </Card>
      </div>
    </div>
  );
}
