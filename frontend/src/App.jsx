import React from "react";
import { Sidebar, TopBar } from "./components.jsx";
import { usePersona } from "./persona.jsx";
import RBALandingView from "./views/RBALandingView.jsx";
import DashboardView from "./views/DashboardView.jsx";
import QueueView from "./views/QueueView.jsx";
import CaseView from "./views/CaseView.jsx";
import NewTransactionView from "./views/NewTransactionView.jsx";
import EscalationQueueView from "./views/EscalationQueueView.jsx";
import HowItWorksView from "./views/HowItWorksView.jsx";
import RulesView from "./views/RulesView.jsx";
import RegulatoryView from "./views/RegulatoryView.jsx";
import AboutView from "./views/AboutView.jsx";

const TITLES = {
  dashboard: "Dashboard",
  queue: "Case queue",
  "new-transaction": "New transaction",
  escalations: "Escalation queue",
  case: (tx) => `Investigation · ${tx}`,
  "how-it-works": "How it works",
  rules: "Detection rules",
  regs: "Regulatory knowledge base",
  about: "About & guardrails",
};

export default function App() {
  const { loggedIn } = usePersona();
  const [view, setView] = React.useState("dashboard");
  const [activeTx, setActiveTx] = React.useState(null);

  const openCase = (txId) => { setActiveTx(txId); setView("case"); };

  if (!loggedIn) return <RBALandingView />;

  return (
    <div style={{ display: "flex", height: "100vh", background: "var(--page)" }}>
      <Sidebar view={view} setView={(v) => { if (v !== "case") setView(v); }} />
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        <TopBar title={view === "case" ? TITLES.case(activeTx) : TITLES[view]} subtitle="India ↔ UAE ↔ Singapore corridor" />
        <div style={{ flex: 1, overflow: "auto", padding: 22 }}>
          {view === "dashboard" && <DashboardView openCase={openCase} />}
          {view === "queue" && <QueueView openCase={openCase} />}
          {view === "new-transaction" && <NewTransactionView openCase={openCase} />}
          {view === "escalations" && <EscalationQueueView openCase={openCase} />}
          {view === "case" && activeTx && <CaseView transactionId={activeTx} />}
          {view === "how-it-works" && <HowItWorksView />}
          {view === "rules" && <RulesView />}
          {view === "regs" && <RegulatoryView />}
          {view === "about" && <AboutView />}
        </div>
      </div>
    </div>
  );
}
