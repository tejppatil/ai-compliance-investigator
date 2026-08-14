import React from "react";
import { Card } from "../components.jsx";
import PipelineFlow from "../components/PipelineFlow.jsx";

const STAGES = [
  { key: "received", label: "Transaction received", status: "done",
    description: "Enters the investigation queue.", file: "aci/orchestrator.py" },
  { key: "transaction", label: "Transaction Intelligence", status: "done",
    description: "Median, ratio, velocity, structuring — pure statistics, no LLM.", file: "aci/agents/transaction_agent.py" },
  { key: "entity", label: "Entity Intelligence", status: "done",
    description: "Shared directors, beneficial-owner chains.", file: "aci/agents/entity_agent.py" },
  { key: "sanctions", label: "Sanctions Screening", status: "done",
    description: "Counterparty + related parties vs a bundled synthetic watchlist. A confirmed match floors the risk band.", file: "aci/agents/sanctions_agent.py" },
  { key: "compliance", label: "Compliance RAG", status: "done",
    description: "Retrieves applicable regulation, jurisdiction-filtered.", file: "aci/agents/compliance_agent.py" },
  { key: "document", label: "Document Analysis", status: "done",
    description: "Invoice ↔ transaction reconciliation.", file: "aci/agents/document_agent.py" },
  { key: "kyc", label: "KYC Completeness", status: "done",
    description: "Onboarding record consistency — not a risk score.", file: "aci/agents/kyc_agent.py" },
  { key: "risk", label: "Risk Engine (RBA)", status: "done",
    description: "Six weighted dimensions combined, explainably.", file: "aci/agents/risk_agent.py" },
  { key: "investigation", label: "Investigation Agent", status: "done",
    description: "Correlates everything, builds the evidence graph.", file: "aci/agents/investigation_agent.py" },
  { key: "tier1", label: "Tier-1 Human Review", status: "done",
    description: "Close, request info/EDD, or escalate.", file: "aci/orchestrator.py" },
  { key: "escalated", label: "Escalated", status: "pending",
    description: "Optional — assigned to a senior reviewer with an SLA.", file: "aci/orchestrator.py" },
  { key: "tier2", label: "Tier-2 Senior Review", status: "pending",
    description: "Only reachable once escalated — enforced server-side.", file: "aci/orchestrator.py" },
  { key: "closed", label: "Closed", status: "pending", description: "Case resolved." },
];

export default function HowItWorksView() {
  return (
    <div>
      <p style={{ color: "var(--muted)", fontSize: 13, marginTop: 0, marginBottom: 24, maxWidth: 680, lineHeight: 1.6 }}>
        Every investigation moves through this exact pipeline — a controlled, ordered sequence
        (<code className="mono">aci/orchestrator.py</code>), not free-roaming agents. Open any case
        and run an investigation to watch this same diagram animate stage by stage in real time.
      </p>
      <Card>
        <div style={{ overflowX: "auto", paddingBottom: 4 }}>
          <PipelineFlow stages={STAGES} />
        </div>
      </Card>
      <div style={{ marginTop: 18, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        <Card>
          <div className="eyebrow" style={{ marginBottom: 8 }}>Why this shape</div>
          <p style={{ fontSize: 12.5, color: "var(--muted)", lineHeight: 1.6, margin: 0 }}>
            A controlled pipeline, not unrestricted autonomous agents. Each stage writes to the
            audit trail before the next one runs, so the sequence itself is part of the evidence —
            see the Investigation Timeline on any case for the same sequence with real timestamps.
          </p>
        </Card>
        <Card>
          <div className="eyebrow" style={{ marginBottom: 8 }}>Where it stops</div>
          <p style={{ fontSize: 12.5, color: "var(--muted)", lineHeight: 1.6, margin: 0 }}>
            The pipeline halts at Tier-1 Human Review. Nothing past that point happens without a
            person clicking a button — including escalation, which only reassigns the case to a
            named senior reviewer, never acts on it automatically.
          </p>
        </Card>
      </div>
    </div>
  );
}
