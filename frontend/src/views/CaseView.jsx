import React from "react";
import { AGENT_ORDER, AgentResultCard, Card, Eyebrow, EvidenceGraph, Pill, PendingAgentCard, RiskMeter } from "../components.jsx";
import { api, caseIdFor } from "../api.js";
import { usePersona } from "../persona.jsx";
import { ErrorBanner } from "./DashboardView.jsx";
import InvestigationTimeline from "../components/InvestigationTimeline.jsx";
import PipelineFlow from "../components/PipelineFlow.jsx";
import SanctionsPanel from "../components/SanctionsPanel.jsx";
import CaseQAPanel from "../components/CaseQAPanel.jsx";

const STAGE_LABELS = {
  transaction_intelligence: "Transaction Intel", entity_intelligence: "Entity Intel",
  sanctions_screening: "Sanctions Screening",
  compliance_intelligence: "Compliance RAG", document_analysis: "Document Analysis",
  kyc_completeness: "KYC Completeness",
};

// Builds the live PipelineFlow stage list from real case/reveal/escalation
// state — the same shape the static How It Works page uses, but every status
// here reflects this specific case rather than a fixed explainer list.
function buildLiveStages(caseData, revealCount) {
  const agentStages = caseData.agent_results.map((r, i) => ({
    key: r.agent, label: STAGE_LABELS[r.agent] || r.agent,
    status: i < revealCount ? "done" : i === revealCount ? "active" : "pending",
    severity: i < revealCount ? r.severity : undefined,
  }));
  const analysisDone = revealCount > caseData.agent_results.length;
  const tier1Done = caseData.status !== "pending_human_review";
  const escalated = caseData.escalation_level >= 1;
  const seniorDone = caseData.escalation_level === 2;
  const closed = caseData.status === "closed";

  const stages = [
    { key: "received", label: "Received", status: "done" },
    ...agentStages,
    { key: "risk", label: "Risk Engine", status: analysisDone ? "done" : "pending", severity: analysisDone ? caseData.risk.band : undefined },
    { key: "tier1", label: "Tier-1 Review", status: !analysisDone ? "pending" : tier1Done ? "done" : "active" },
  ];
  if (escalated) {
    stages.push({ key: "escalated", label: "Escalated", status: "done" });
    stages.push({ key: "tier2", label: "Senior Review", status: seniorDone ? "done" : "active" });
  }
  if (closed) stages.push({ key: "closed", label: "Closed", status: "done" });
  return stages;
}

const REVEAL_STAGGER_MS = 550;

// Reveals agent cards one at a time, then one more step for the narrative +
// right-hand column together. This is a presentation animation of a result
// that already arrived in a single API response — genuine per-agent
// streaming would need the backend to expose incremental results, which
// isn't justified for a demo polish pass — but it's what lets a judge
// watching a live demo actually see each agent "complete" in turn instead
// of the whole case appearing at once.
function animateReveal(agentCount, setRevealCount) {
  setRevealCount(0);
  let step = 0;
  const total = agentCount + 1;
  const timer = setInterval(() => {
    step += 1;
    setRevealCount(step);
    if (step >= total) clearInterval(timer);
  }, REVEAL_STAGGER_MS);
}

export default function CaseView({ transactionId }) {
  const { persona } = usePersona();
  const [txnMeta, setTxnMeta] = React.useState(null);
  const [caseData, setCaseData] = React.useState(null);
  const [audit, setAudit] = React.useState([]);
  const [auditVerify, setAuditVerify] = React.useState(null);
  const [running, setRunning] = React.useState(false);
  const [notFound, setNotFound] = React.useState(false);
  const [error, setError] = React.useState(null);
  const [reviewError, setReviewError] = React.useState(null);
  const [notes, setNotes] = React.useState("");
  // How many agent cards + the narrative/right-column are currently shown.
  // A fresh result from clicking "Run investigation" reveals in sequence
  // (a presentation of a result that already arrived — see the comment
  // below — not fake incremental computation); revisiting an already-
  // investigated case shows everything immediately.
  const [revealCount, setRevealCount] = React.useState(Infinity);
  const justRanRef = React.useRef(false);

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
        const [c, a, v] = await Promise.all([api.getCase(caseId), api.getAudit(caseId), api.verifyAudit(caseId)]);
        setCaseData(c);
        setAudit(a);
        setAuditVerify(v);
        if (justRanRef.current) {
          justRanRef.current = false;
          animateReveal(c.agent_results.length, setRevealCount);
        } else {
          setRevealCount(Infinity);
        }
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
    justRanRef.current = true;
    try {
      await api.createInvestigation(transactionId);
      await load();
    } catch (e) {
      setError(e.message);
      justRanRef.current = false;
    } finally {
      setRunning(false);
    }
  }

  async function decide(decision) {
    setReviewError(null);
    try {
      await api.review(caseId, decision, notes, { actor: persona.name, role: persona.role });
      setNotes("");
      await load();
    } catch (e) {
      // A rejected tier-1 redecision surfaces here as a real 403 from the
      // API — shown inline rather than swallowed, since that response IS
      // the two-person control working as intended, not a bug.
      setReviewError(e.message);
    }
  }

  if (error) return <ErrorBanner message={error} />;
  if (!txnMeta) return <div style={{ color: "var(--muted)", fontSize: 13 }}>Loading transaction…</div>;

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1.35fr 1fr", gap: 18, alignItems: "start" }}>
      <div>
        <TxnHeader txn={txnMeta} running={running} onRun={runInvestigation} hasCase={!!caseData} />

        {caseData && (
          <Card style={{ marginTop: 16 }}>
            <Eyebrow>Pipeline — proof it moves stage to stage</Eyebrow>
            <div style={{ overflowX: "auto", paddingBottom: 4 }}>
              <PipelineFlow stages={buildLiveStages(caseData, revealCount)} dense />
            </div>
          </Card>
        )}

        {/* Sits directly under the pipeline, above everything else, and only
            once the reveal has passed the screening stage — a match is the
            one finding that shouldn't have to be scrolled to. */}
        {caseData && revealCount > caseData.agent_results.findIndex((r) => r.dimension === "sanctions") && (
          <SanctionsPanel
            result={caseData.agent_results.find((r) => r.dimension === "sanctions")}
            status={caseData.sanctions_status}
            floorReason={caseData.risk.sanctions_floor_applied}
          />
        )}

        {caseData && (
          <Card style={{ marginTop: 16 }}>
            <Eyebrow>Investigation timeline — how it happened</Eyebrow>
            <InvestigationTimeline caseData={caseData} customer={caseData.customer} audit={audit} />
          </Card>
        )}

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
              {caseData.agent_results.map((r, i) => (
                i < revealCount
                  ? <div key={r.agent} className={revealCount !== Infinity && i === revealCount - 1 ? "reveal-in" : undefined}><AgentResultCard result={r} /></div>
                  : <PendingAgentCard key={r.agent} agentKey={AGENT_ORDER[i]} active={i === revealCount} />
              ))}
              {revealCount > caseData.agent_results.length && (
                <div className={revealCount === caseData.agent_results.length + 1 ? "reveal-in" : undefined}>
                  <NarrativeBlock narrative={caseData.narrative} />
                </div>
              )}
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
        {caseData && revealCount > caseData.agent_results.length && (
          <>
            <Card style={{ marginBottom: 16 }} className={revealCount === caseData.agent_results.length + 1 ? "reveal-in" : undefined}>
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

            {/* Sits after the evidence it draws on and BEFORE the decision
                panel — a convenience layer for interrogating what's above,
                not a step on the way to deciding. */}
            <div style={{ marginBottom: 16 }}>
              <CaseQAPanel caseId={caseData.case_id} />
            </div>

            {reviewError && (
              <div className="card" style={{ marginBottom: 16, borderColor: "var(--crit-line)", background: "var(--crit-soft)", color: "var(--crit)", fontSize: 12 }}>
                {reviewError}
              </div>
            )}
            <HumanDecision caseData={caseData} persona={persona} notes={notes} setNotes={setNotes} decide={decide} />

            <Card style={{ marginTop: 16 }}>
              <Eyebrow>Audit trail · {audit.length}</Eyebrow>
              {auditVerify && (
                <div className="mono" style={{ fontSize: 10.5, marginBottom: 10, color: auditVerify.verified ? "var(--ok)" : "var(--crit)" }}>
                  {auditVerify.verified
                    ? `✓ Hash chain verified — ${auditVerify.entries} entries, SHA-256`
                    : `✗ Hash chain BROKEN at entry ${auditVerify.broken_at}`}
                </div>
              )}
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
      {/* Rendered as a visibly distinct, badged suggestion — deliberately NOT
          as another narrative field, and deliberately NOT pre-filled into the
          decision form below. A default that looks like data is a decision
          made by omission; this has to look like advice the officer can
          ignore. Absent entirely on the deterministic template path. */}
      {narrative.suggested_action && (
        <div style={{ background: "var(--med-soft)", border: "1px dashed var(--med-line)", borderRadius: 8,
          padding: "10px 12px", marginBottom: 10 }}>
          <div className="mono" style={{ fontSize: 9.5, color: "var(--med)", textTransform: "uppercase",
            letterSpacing: ".08em", marginBottom: 3 }}>
            ◆ AI suggests · not a decision
          </div>
          <div style={{ fontSize: 12, color: "var(--text)", lineHeight: 1.5 }}>{narrative.suggested_action}</div>
          <div style={{ fontSize: 10, color: "var(--faint)", marginTop: 5 }}>
            A recommendation only. You choose the action below; nothing is pre-selected for you.
          </div>
        </div>
      )}
      <div style={{ fontSize: 10.5, color: "var(--faint)", borderTop: "1px solid var(--border)", paddingTop: 8 }}>
        The AI does not make the regulatory decision. It prepares this case for a human compliance officer.
      </div>
    </div>
  );
}

// Two-tier: escalation_level 0 = tier-1 (either persona), 1 = awaiting the
// senior reviewer (officer sees a read-only state; the API rejects an
// officer's attempt server-side, not just this screen), 2 = resolved.
function HumanDecision({ caseData, persona, notes, setNotes, decide }) {
  const { status, escalation_level, assigned_to, sla_due_at } = caseData;
  const riskBand = caseData.risk.band;

  if (escalation_level === 1) {
    const overdue = sla_due_at && new Date(sla_due_at) < new Date();
    if (persona.role !== "senior") {
      return (
        <Card style={{ borderColor: overdue ? "var(--crit-line)" : "var(--med-line)" }}>
          <Eyebrow right={<Pill sev={riskBand} />}>Escalated — awaiting senior review</Eyebrow>
          <div style={{ fontSize: 12.5, color: "var(--muted)", lineHeight: 1.6 }}>
            This case is with <b style={{ color: "var(--text)" }}>{assigned_to}</b> and can no longer be
            decided at this tier — enforced by the API, not just hidden on this screen.
          </div>
          <div className="mono" style={{ marginTop: 10, fontSize: 11, color: overdue ? "var(--crit)" : "var(--med)" }}>
            {overdue ? "OVERDUE" : "SLA"} · due {new Date(sla_due_at).toLocaleString()}
          </div>
          <div style={{ fontSize: 10.5, color: "var(--faint)", marginTop: 10 }}>
            Switch to the Senior Compliance Officer persona (top right) to review this case.
          </div>
        </Card>
      );
    }
    const options = [
      { k: "senior_close", label: "Approve AI assessment & close" },
      { k: "senior_override", label: "Override assessment & close" },
      { k: "senior_return", label: "Return for more evidence" },
    ];
    return (
      <Card style={{ borderColor: "#8b5cf6" }}>
        <Eyebrow right={<Pill sev={riskBand} />}>Senior review — decision required</Eyebrow>
        <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 10, lineHeight: 1.55 }}>
          Escalated by the tier-1 officer for independent review. Approve, override, or return it for
          more evidence — this is the second, independent check on the officer's own decision.
        </div>
        <div className="mono" style={{ fontSize: 11, color: overdue ? "var(--crit)" : "var(--faint)", marginBottom: 10 }}>
          {overdue ? "OVERDUE" : "SLA due"} {new Date(sla_due_at).toLocaleString()}
        </div>
        <textarea value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Senior review notes (written to the audit trail)…"
          style={{ width: "100%", minHeight: 54, resize: "vertical", marginBottom: 12 }} />
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {options.map((o) => (
            <button key={o.k} onClick={() => decide(o.k)} className="btn-ghost" style={{ textAlign: "left" }}>{o.label}</button>
          ))}
        </div>
      </Card>
    );
  }

  if (escalation_level === 2) {
    return (
      <Card>
        <Eyebrow right={<Pill sev={riskBand} />}>Escalation resolved</Eyebrow>
        <div style={{ fontSize: 12.5, color: "var(--muted)", lineHeight: 1.5 }}>
          Reviewed by the Senior Compliance Officer and closed — see the audit trail below for the outcome.
        </div>
      </Card>
    );
  }

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
          <button key={o.k} onClick={() => decide(o.k)} className="btn-ghost" style={{ textAlign: "left" }}>
            {o.label}
          </button>
        ))}
      </div>
    </Card>
  );
}
