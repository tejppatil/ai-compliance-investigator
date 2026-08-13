import React from "react";
import { Card, Eyebrow, Pill, RiskMeter, AgentResultCard, EvidenceGraph } from "../components.jsx";
import { api, caseIdFor } from "../api.js";
import { ErrorBanner } from "./DashboardView.jsx";

export default function CaseView({ transactionId }) {
  const [txnMeta, setTxnMeta] = React.useState(null);
  const [caseData, setCaseData] = React.useState(null);
  const [audit, setAudit] = React.useState([]);
  const [running, setRunning] = React.useState(false);
  const [notFound, setNotFound] = React.useState(false);
  const [error, setError] = React.useState(null);
  const [notes, setNotes] = React.useState("");

  const caseId = caseIdFor(transactionId);

  const load = React.useCallback(async () => {
    setError(null);
    try {
      // Check the case list first rather than GETting the case and catching a
      // 404 — a not-yet-investigated transaction is an ordinary state, not an
      // error, and shouldn't spray failed requests into the browser console.
      const [txns, existing] = await Promise.all([api.listTransactions(), api.listInvestigations()]);
      setTxnMeta(txns.find((t) => t.transaction_id === transactionId));
      const hasCase = existing.some((c) => c.case_id === caseId);
      if (hasCase) {
        const [c, a] = await Promise.all([api.getCase(caseId), api.getAudit(caseId)]);
        setCaseData(c);
        setAudit(a);
      } else {
        setCaseData(null);
        setAudit([]);
      }
      setNotFound(!hasCase);
    } catch (e) {
      setError(e.message);
    }
  }, [transactionId, caseId]);

  React.useEffect(() => { load(); }, [load]);

  async function runInvestigation() {
    setRunning(true);
    setError(null);
    try {
      await api.createInvestigation(transactionId);
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setRunning(false);
    }
  }

  async function decide(decision, label) {
    try {
      await api.review(caseId, decision, notes);
      await load();
    } catch (e) {
      setError(e.message);
    }
  }

  if (error) return <ErrorBanner message={error} />;
  if (!txnMeta) return <div style={{ color: "var(--muted)", fontSize: 13 }}>Loading transaction…</div>;

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1.35fr 1fr", gap: 18, alignItems: "start" }}>
      <div>
        <TxnHeader txn={txnMeta} running={running} onRun={runInvestigation} hasCase={!!caseData} />

        <Card style={{ marginTop: 16 }}>
          <Eyebrow right={caseData && <Pill sev="none">{caseData.narrative.source === "ai" ? "AI NARRATIVE" : "TEMPLATE"}</Pill>}>
            Multi-agent orchestration
          </Eyebrow>
          {notFound && !running && (
            <div style={{ textAlign: "center", padding: "26px 10px" }}>
              <div style={{ fontSize: 12.5, color: "var(--muted)", maxWidth: 380, margin: "0 auto 16px", lineHeight: 1.55 }}>
                Four specialised agents will analyse this transaction from different angles — behaviour, entities,
                regulation, documents — then an explainable risk engine and investigation agent correlate the
                evidence into one case for your review.
              </div>
              <button className="btn-primary" onClick={runInvestigation} disabled={running}>Run investigation</button>
            </div>
          )}
          {running && <div className="mono blink" style={{ fontSize: 12, color: "var(--accent)", padding: "10px 0" }}>Investigating… (local model may take up to a minute on CPU)</div>}
          {caseData && (
            <div>
              {caseData.agent_results.map((r) => <AgentResultCard key={r.agent} result={r} />)}
              <NarrativeBlock narrative={caseData.narrative} />
            </div>
          )}
        </Card>

        {caseData && caseData.unknowns.length > 0 && (
          <Card style={{ marginTop: 16 }}>
            <Eyebrow>Unknown information</Eyebrow>
            {caseData.unknowns.map((u, i) => (
              <div key={i} style={{ fontSize: 12, color: "var(--muted)", padding: "3px 0", lineHeight: 1.5 }}>- {u}</div>
            ))}
          </Card>
        )}

        {caseData && (
          <Card style={{ marginTop: 16 }}>
            <Eyebrow>Recommended next steps</Eyebrow>
            {caseData.recommended_actions.map((a, i) => (
              <div key={i} style={{ fontSize: 12, color: "var(--muted)", padding: "3px 0", lineHeight: 1.5 }}>{i + 1}. {a}</div>
            ))}
          </Card>
        )}
      </div>

      <div>
        {caseData && (
          <>
            <Card style={{ marginBottom: 16 }}>
              <Eyebrow>Explainable risk</Eyebrow>
              <RiskMeter risk={caseData.risk} />
            </Card>

            <Card style={{ marginBottom: 16 }}>
              <Eyebrow right={<Pill sev="none">SIGNATURE</Pill>}>Evidence graph</Eyebrow>
              <EvidenceGraph graph={caseData.graph} />
            </Card>

            <Card style={{ marginBottom: 16 }}>
              <Eyebrow>Evidence · {caseData.evidence.length}</Eyebrow>
              {caseData.evidence.map((e) => (
                <div key={e.id} style={{ display: "flex", gap: 10, padding: "7px 0", borderBottom: "1px solid var(--hair)" }}>
                  <span className="mono" style={{ fontSize: 10.5, color: "var(--accent)", flexShrink: 0, paddingTop: 1 }}>{e.id}</span>
                  <div>
                    <div className="mono" style={{ fontSize: 9.5, color: "var(--faint)", textTransform: "uppercase" }}>{e.source_type}</div>
                    <div style={{ fontSize: 11.5, color: "var(--muted)", lineHeight: 1.45 }}>{e.content}</div>
                  </div>
                </div>
              ))}
            </Card>

            <HumanDecision status={caseData.status} riskBand={caseData.risk.band} notes={notes} setNotes={setNotes} decide={decide} />

            <Card style={{ marginTop: 16 }}>
              <Eyebrow>Audit trail · {audit.length}</Eyebrow>
              <div style={{ maxHeight: 220, overflow: "auto" }}>
                {audit.map((a, i) => (
                  <div key={i} style={{ display: "flex", gap: 9, padding: "4px 0", fontSize: 11, lineHeight: 1.45 }}>
                    <span className="mono" style={{ color: "var(--faint)", flexShrink: 0, width: 90 }}>{new Date(a.ts).toLocaleTimeString()}</span>
                    <span className="mono" style={{ color: a.actor === "human" ? "var(--ok)" : "var(--faint)", flexShrink: 0, width: 46 }}>{a.actor}</span>
                    <span style={{ color: "var(--muted)" }}>{a.action}</span>
                  </div>
                ))}
              </div>
            </Card>
          </>
        )}
      </div>
    </div>
  );
}

function TxnHeader({ txn, running, onRun, hasCase }) {
  return (
    <Card>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div className="mono" style={{ fontSize: 12, color: "var(--accent)" }}>{txn.transaction_id}</div>
          <div style={{ fontSize: 22, fontWeight: 700, marginTop: 2, fontFamily: "var(--font-display)" }}>
            ₹{txn.amount.toLocaleString("en-IN")}
          </div>
        </div>
        <button className="btn-primary" onClick={onRun} disabled={running}>
          {running ? "Investigating…" : hasCase ? "Re-run" : "Run investigation"}
        </button>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px 22px", marginTop: 16 }}>
        {[["Customer", txn.customer], ["Route", txn.route.join(" → ")], ["Purpose", txn.purpose]].map(([k, v]) => (
          <div key={k}>
            <div className="mono" style={{ fontSize: 9.5, color: "var(--faint)", textTransform: "uppercase" }}>{k}</div>
            <div style={{ fontSize: 12.5, marginTop: 1 }}>{v}</div>
          </div>
        ))}
      </div>
    </Card>
  );
}

function NarrativeBlock({ narrative }) {
  const parts = [["What happened", narrative.what_happened], ["Why it's unusual", narrative.why_unusual],
    ["Who is involved", narrative.who_involved], ["Conclusion", narrative.conclusion]];
  return (
    <div style={{ background: "var(--sunken)", border: "1px solid var(--border)", borderRadius: 8, padding: 14, marginTop: 8 }}>
      {parts.map(([k, v]) => (
        <div key={k} style={{ marginBottom: 9 }}>
          <div className="mono" style={{ fontSize: 9.5, color: "var(--accent)", textTransform: "uppercase", letterSpacing: ".08em", marginBottom: 2 }}>{k}</div>
          <div style={{ fontSize: 12, color: "var(--muted)", lineHeight: 1.5 }}>{v}</div>
        </div>
      ))}
      <div style={{ fontSize: 10.5, color: "var(--faint)", borderTop: "1px solid var(--border)", paddingTop: 8 }}>
        The AI does not make the regulatory decision. It prepares this case for a human compliance officer.
      </div>
    </div>
  );
}

function HumanDecision({ status, riskBand, notes, setNotes, decide }) {
  const options = [
    { k: "edd", label: "Request enhanced due diligence" },
    { k: "escalate", label: "Escalate to senior officer" },
    { k: "info", label: "Request more information" },
    { k: "close", label: "Close — no action" },
  ];
  const decided = status !== "pending_human_review";
  return (
    <Card style={{ borderColor: "var(--accent)" }}>
      <Eyebrow right={<Pill sev={riskBand} />}>Human decision {decided ? `— recorded (${status.replace(/_/g, " ")})` : "— required"}</Eyebrow>
      <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 12, lineHeight: 1.5 }}>
        The system has assembled the case. The final regulatory decision is yours. No account is frozen,
        no report filed, and no customer rejected by the AI.
      </div>
      <textarea value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Add reviewer notes (written to the audit trail)…"
        style={{ width: "100%", minHeight: 54, resize: "vertical", marginBottom: 12 }} />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
        {options.map((o) => (
          <button key={o.k} onClick={() => decide(o.k, o.label)} className="btn-ghost" style={{ textAlign: "left" }}>
            {o.label}
          </button>
        ))}
      </div>
    </Card>
  );
}
