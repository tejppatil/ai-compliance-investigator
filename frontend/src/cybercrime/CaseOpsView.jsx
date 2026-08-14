import React from "react";
import { Card, Eyebrow } from "../components.jsx";
import { api } from "../api.js";
import { usePersona } from "../persona.jsx";
import { CyberPill } from "./shared.jsx";

const HOP_LABELS = ["Source account", "Mule hop 1", "Mule hop 2", "Cash-out / crypto"];

// `transactions` is the shared live feed from CyberModuleShell (one
// WebSocket connection for the whole module, not one per view).
export default function CaseOpsView({ caseId, setCaseId, transactions = [] }) {
  const { persona } = usePersona();
  const [cases, setCases] = React.useState(null);
  const [error, setError] = React.useState(null);
  const [busyHop, setBusyHop] = React.useState(null);
  const [justHit, setJustHit] = React.useState(null); // {hop, ts} — a live tx touched this case's chain

  const load = React.useCallback(() => {
    api.cyberCases().then((c) => {
      setCases(c);
      if (!caseId && c.length) setCaseId(c[0].case_id);
    }).catch((e) => setError(e.message));
  }, [caseId, setCaseId]);
  React.useEffect(() => { load(); const t = setInterval(load, 5000); return () => clearInterval(t); }, [load]);

  const activeCase = cases?.find((c) => c.case_id === caseId) || cases?.[0];

  // Real cross-reference, not staged: if the live feed produces a
  // transaction whose destination matches an account in THIS case's chain,
  // that's a genuine "money is moving on this exact case right now" moment.
  React.useEffect(() => {
    if (!activeCase || transactions.length === 0) return;
    const latest = transactions[0];
    const hop = activeCase.layering_path.indexOf(latest.destination_account);
    if (hop > 0) setJustHit({ hop, ts: latest.ts, tx: latest });
  }, [transactions, activeCase]);

  async function freeze(hopIndex) {
    if (!activeCase) return;
    setBusyHop(hopIndex);
    try { await api.cyberFreezeHop(activeCase.case_id, hopIndex, persona.name); await load(); }
    catch (e) { setError(e.message); }
    finally { setBusyHop(null); }
  }

  if (error) return <div className="card" style={{ color: "var(--crit)", fontSize: 13 }}>{error}</div>;
  if (!cases) return <div style={{ color: "var(--muted)", fontSize: 13 }}>Loading case ops…</div>;
  if (!activeCase) return <div style={{ color: "var(--muted)", fontSize: 13 }}>No cases yet.</div>;

  return (
    <div>
      <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 16 }}>
        <select value={activeCase.case_id} onChange={(e) => setCaseId(e.target.value)}
          style={{ fontSize: 12.5, padding: "8px 10px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--sunken)", color: "var(--text)" }}>
          {cases.map((c) => <option key={c.case_id} value={c.case_id}>{c.case_id} — {c.title}</option>)}
        </select>
        <CyberPill severity={activeCase.severity} />
        <span style={{ fontSize: 11.5, color: "var(--muted)" }}>{activeCase.status}</span>
      </div>

      <Card style={{ marginBottom: 16 }}>
        <Eyebrow right={<span className="mono" style={{ fontSize: 10, color: "var(--faint)" }}>₹{activeCase.amount.toLocaleString("en-IN")}</span>}>
          Layering flow — money moving hop to hop
        </Eyebrow>
        <div style={{ display: "flex", alignItems: "stretch", gap: 0, overflowX: "auto", padding: "10px 0" }}>
          {activeCase.layering_path.map((account, i) => {
            const frozen = activeCase.frozen_hops.includes(i);
            const hot = justHit?.hop === i && Date.now() - new Date(justHit.ts).getTime() < 15000;
            return (
              <React.Fragment key={i}>
                {i > 0 && (
                  <div style={{ display: "flex", alignItems: "center", padding: "0 4px", flexShrink: 0 }}>
                    <div style={{ width: 34, height: 2, background: hot ? "var(--crit)" : "var(--border)" }} />
                    <span style={{ color: hot ? "var(--crit)" : "var(--faint)", fontSize: 13 }}>▶</span>
                  </div>
                )}
                <div style={{ minWidth: 160, flexShrink: 0, border: `1.5px solid ${frozen ? "var(--crit)" : hot ? "var(--crit)" : "var(--border)"}`,
                  background: frozen ? "var(--crit-soft)" : hot ? "var(--crit-soft)" : "var(--sunken)", borderRadius: 10, padding: 12 }}>
                  <div className="mono" style={{ fontSize: 9, color: "var(--faint)", textTransform: "uppercase" }}>{HOP_LABELS[i] || `Hop ${i}`}</div>
                  <div className="mono" style={{ fontSize: 12, fontWeight: 600, color: "var(--text)", margin: "3px 0" }}>{account}</div>
                  {frozen && <div className="mono" style={{ fontSize: 9.5, color: "var(--crit)" }}>🔒 FROZEN</div>}
                  {hot && !frozen && <div className="mono blink" style={{ fontSize: 9.5, color: "var(--crit)" }}>● LIVE HIT</div>}
                  {i > 0 && !frozen && (
                    <button className="btn-ghost" disabled={busyHop === i} onClick={() => freeze(i)}
                      style={{ marginTop: 6, padding: "4px 8px", fontSize: 10, color: "var(--crit)", borderColor: "var(--crit-line)" }}>
                      ⛔ Trigger holding freeze
                    </button>
                  )}
                </div>
              </React.Fragment>
            );
          })}
        </div>
        <div style={{ fontSize: 10.5, color: "var(--faint)", marginTop: 8 }}>
          A freeze here is this officer's own action — logged immediately below — never something the rule engine does on its own.
        </div>
      </Card>

      <Card>
        <Eyebrow>Case history</Eyebrow>
        <div style={{ maxHeight: 260, overflowY: "auto" }}>
          {[...activeCase.history].reverse().map((h, i) => (
            <div key={i} style={{ display: "flex", gap: 9, padding: "6px 0", fontSize: 11.5, borderBottom: "1px solid var(--hair)" }}>
              <span className="mono" style={{ color: "var(--faint)", flexShrink: 0, width: 130 }}>{new Date(h.ts).toLocaleString()}</span>
              <span className="mono" style={{ color: h.actor === "system" ? "var(--faint)" : "var(--ok)", flexShrink: 0, width: 90, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{h.actor}</span>
              <span style={{ color: "var(--muted)" }}>{h.action}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
