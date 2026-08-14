import React from "react";
import { CyberSidebar, TopBar } from "../components.jsx";
import { usePersona } from "../persona.jsx";
import { useLiveFeed } from "./useLiveFeed.js";
import AlertToast from "./AlertToast.jsx";
import CommandCenterView from "./CommandCenterView.jsx";
import CaseOpsView from "./CaseOpsView.jsx";
import TransactionFeedView from "./TransactionFeedView.jsx";
import HeatMapView from "./HeatMapView.jsx";
import IntelGraphView from "./IntelGraphView.jsx";

const TITLES = {
  command: "Command Center",
  "case-ops": "Case Ops — live layering flow",
  feed: "Transaction Feed",
  heatmap: "Cyber Crime Heat Map",
  intel: "Intelligence Link Network",
};

// Each role lands on the view built for it — the Nodal lead on the
// cross-officer overview, the IO on operational case work, the analyst on
// the transaction stream. Every view stays reachable from the sidebar
// regardless, so a single demo operator can walk the whole system.
const DEFAULT_VIEW = { nodal: "command", io: "case-ops", analyst: "feed" };

export default function CyberModuleShell() {
  const { persona } = usePersona();
  const [view, setView] = React.useState(() => DEFAULT_VIEW[persona.role] || "command");
  const [caseId, setCaseId] = React.useState(null);

  // One WebSocket for the whole module, shared down to every view that needs
  // it — opening a separate connection per page would multiply the feed.
  const { transactions, connected, lastFlagged } = useLiveFeed();

  // Switching role mid-demo re-lands on that role's home view, matching what
  // signing in as them would have done.
  const lastRole = React.useRef(persona.role);
  React.useEffect(() => {
    if (lastRole.current !== persona.role) {
      lastRole.current = persona.role;
      setView(DEFAULT_VIEW[persona.role] || "command");
    }
  }, [persona.role]);

  const openCase = (id) => { setCaseId(id); setView("case-ops"); };

  return (
    <div style={{ display: "flex", height: "100vh", background: "var(--page)" }}>
      <CyberSidebar view={view} setView={setView} />
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        <TopBar title={TITLES[view]} subtitle={connected ? "● live feed connected" : "○ feed reconnecting…"} />
        {/* extra bottom padding so scrollable content can always clear the
            fixed alert-toast zone in the bottom-right corner */}
        <div style={{ flex: 1, overflow: "auto", padding: "22px 22px 200px" }}>
          {view === "command" && <CommandCenterView openCase={openCase} />}
          {view === "case-ops" && <CaseOpsView caseId={caseId} setCaseId={setCaseId} transactions={transactions} />}
          {view === "feed" && <TransactionFeedView transactions={transactions} connected={connected} />}
          {view === "heatmap" && <HeatMapView />}
          {view === "intel" && <IntelGraphView caseId={caseId} setCaseId={setCaseId} />}
        </div>
      </div>
      <AlertToast lastFlagged={lastFlagged} />
    </div>
  );
}
