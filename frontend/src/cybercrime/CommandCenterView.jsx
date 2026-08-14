import React from "react";
import { Card, Eyebrow, Pill } from "../components.jsx";
import { api } from "../api.js";
import { usePersona } from "../persona.jsx";
import { CyberPill, StatusDot, timeAgo } from "./shared.jsx";

const ROLE_LABEL = { nodal: "Nodal Lead", io: "Investigation Officer", analyst: "Analyst" };

export default function CommandCenterView({ openCase }) {
  const { persona } = usePersona();
  const [officers, setOfficers] = React.useState(null);
  const [cases, setCases] = React.useState(null);
  const [error, setError] = React.useState(null);
  const [transferTarget, setTransferTarget] = React.useState({});
  const [busy, setBusy] = React.useState(null);

  const load = React.useCallback(() => {
    Promise.all([api.cyberOfficers(), api.cyberCases()])
      .then(([o, c]) => { setOfficers(o); setCases(c); })
      .catch((e) => setError(e.message));
  }, []);
  React.useEffect(() => { load(); const t = setInterval(load, 5000); return () => clearInterval(t); }, [load]);

  async function escalate(caseId) {
    setBusy(caseId);
    try { await api.cyberEscalate(caseId, persona.name, "Escalated from Command Center."); await load(); }
    catch (e) { setError(e.message); }
    finally { setBusy(null); }
  }

  async function transfer(caseId) {
    const target = transferTarget[caseId];
    if (!target) return;
    setBusy(caseId);
    try { await api.cyberTransfer(caseId, target, persona.name); await load(); }
    catch (e) { setError(e.message); }
    finally { setBusy(null); }
  }

  if (error) return <div className="card" style={{ color: "var(--crit)", fontSize: 13 }}>{error}</div>;
  if (!officers || !cases) return <div style={{ color: "var(--muted)", fontSize: 13 }}>Loading command center…</div>;

  const officerById = Object.fromEntries(officers.map((o) => [o.officer_id, o]));

  return (
    <div>
      <p style={{ color: "var(--muted)", fontSize: 13, marginTop: 0, marginBottom: 18, maxWidth: 680, lineHeight: 1.55 }}>
        Real-time view across every active officer and case — who's assigned to what, their current
        status, and the most recent action they took. Escalate a case to the Nodal lead, or transfer
        ownership between officers, from here.
      </p>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
        <Card>
          <div className="kpi-label">Active officers</div>
          <div className="kpi-value">{officers.filter((o) => o.status !== "Available").length}<span style={{ fontSize: 15, color: "var(--faint)" }}> / {officers.length}</span></div>
        </Card>
        <Card>
          <div className="kpi-label">Escalated to Nodal</div>
          <div className="kpi-value" style={{ color: cases.some((c) => c.escalation_level === 1) ? "var(--med)" : undefined }}>
            {cases.filter((c) => c.escalation_level === 1).length}
          </div>
        </Card>
      </div>

      <Card style={{ marginBottom: 16, padding: 0 }}>
        <div style={{ padding: "14px 18px 0" }}><Eyebrow>Officer activity stream</Eyebrow></div>
        <table>
          <thead><tr><th>Officer</th><th>Role</th><th>Status</th><th>Assigned case</th><th>Last action</th></tr></thead>
          <tbody>
            {officers.map((o) => (
              <tr key={o.officer_id}>
                <td><b>{o.name}</b> <span className="mono" style={{ fontSize: 10, color: "var(--faint)" }}>{o.badge_id}</span></td>
                <td style={{ fontSize: 11.5, color: "var(--muted)" }}>{ROLE_LABEL[o.role] || o.role}</td>
                <td><StatusDot status={o.status} /></td>
                <td className="mono" style={{ fontSize: 11.5 }}>
                  {o.assigned_case_id
                    ? <span style={{ color: "var(--accent)", cursor: "pointer" }} onClick={() => openCase?.(o.assigned_case_id)}>{o.assigned_case_id}</span>
                    : <span style={{ color: "var(--faint)" }}>—</span>}
                </td>
                <td style={{ fontSize: 11.5, color: "var(--muted)" }}>{o.last_action} · <span className="mono" style={{ fontSize: 10, color: "var(--faint)" }}>{timeAgo(o.last_action_at)}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Card style={{ padding: 0 }}>
        <div style={{ padding: "14px 18px 0" }}><Eyebrow>Active cases</Eyebrow></div>
        <table>
          <thead><tr><th>Case</th><th>Crime type</th><th>Severity</th><th>Status</th><th>Assigned to</th><th>Actions</th></tr></thead>
          <tbody>
            {cases.map((c) => (
              <tr key={c.case_id}>
                <td className="mono" style={{ fontSize: 11.5, color: "var(--accent)", cursor: "pointer" }} onClick={() => openCase?.(c.case_id)}>{c.case_id}</td>
                <td style={{ fontSize: 12 }}>{c.crime_type}</td>
                <td><CyberPill severity={c.severity} /></td>
                <td style={{ fontSize: 11.5, color: "var(--muted)" }}>{c.status}</td>
                <td style={{ fontSize: 11.5 }}>{c.assigned_officer_id ? officerById[c.assigned_officer_id]?.name : "Unassigned"}</td>
                <td>
                  <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                    <button className="btn-ghost" disabled={busy === c.case_id || c.escalation_level === 1}
                      onClick={() => escalate(c.case_id)} style={{ padding: "5px 9px", fontSize: 11 }}>
                      Escalate
                    </button>
                    <select value={transferTarget[c.case_id] || ""} onChange={(e) => setTransferTarget((t) => ({ ...t, [c.case_id]: e.target.value }))}
                      style={{ fontSize: 11, padding: "4px 6px", borderRadius: 6, border: "1px solid var(--border)", background: "var(--sunken)", color: "var(--text)" }}>
                      <option value="">Transfer to…</option>
                      {officers.filter((o) => o.officer_id !== c.assigned_officer_id).map((o) => (
                        <option key={o.officer_id} value={o.officer_id}>{o.name}</option>
                      ))}
                    </select>
                    <button className="btn-ghost" disabled={busy === c.case_id || !transferTarget[c.case_id]}
                      onClick={() => transfer(c.case_id)} style={{ padding: "5px 9px", fontSize: 11 }}>
                      Go
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
