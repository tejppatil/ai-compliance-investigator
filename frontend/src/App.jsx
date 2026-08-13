import React from "react";
import { Sidebar, TopBar } from "./components.jsx";
import DashboardView from "./views/DashboardView.jsx";
import QueueView from "./views/QueueView.jsx";
import CaseView from "./views/CaseView.jsx";
import RegulatoryView from "./views/RegulatoryView.jsx";
import AboutView from "./views/AboutView.jsx";

const TITLES = {
  dashboard: "Dashboard",
  queue: "Case queue",
  case: (tx) => `Investigation · ${tx}`,
  regs: "Regulatory knowledge base",
  about: "About & guardrails",
};

export default function App() {
  const [view, setView] = React.useState("dashboard");
  const [activeTx, setActiveTx] = React.useState(null);

  const openCase = (txId) => { setActiveTx(txId); setView("case"); };

  return (
    <div style={{ display: "flex", height: "100vh", background: "var(--page)" }}>
      <Sidebar view={view} setView={(v) => { if (v !== "case") setView(v); }} />
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        <TopBar title={view === "case" ? TITLES.case(activeTx) : TITLES[view]} subtitle="India ↔ UAE ↔ Singapore corridor" />
        <div style={{ flex: 1, overflow: "auto", padding: 22 }}>
          {view === "dashboard" && <DashboardView openCase={openCase} />}
          {view === "queue" && <QueueView openCase={openCase} />}
          {view === "case" && activeTx && <CaseView transactionId={activeTx} />}
          {view === "regs" && <RegulatoryView />}
          {view === "about" && <AboutView />}
        </div>
      </div>
    </div>
  );
}
