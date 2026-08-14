import React from "react";
import { CYBER_WS_URL } from "../api.js";

// Consumes the real backend WebSocket (aci/api/cybercrime_routes.py
// /ws/cyber/transactions) — the simulator ticks server-side every ~2.5s and
// pushes each transaction to every connected client; this hook just keeps a
// bounded rolling buffer and reconnects if the socket drops. No polling.
const BUFFER_SIZE = 300;

export function useLiveFeed() {
  const [transactions, setTransactions] = React.useState([]);
  const [connected, setConnected] = React.useState(false);
  const [lastFlagged, setLastFlagged] = React.useState(null);

  React.useEffect(() => {
    let ws;
    let closedByUs = false;
    let retryTimer;

    function connect() {
      ws = new WebSocket(CYBER_WS_URL);
      ws.onopen = () => setConnected(true);
      ws.onclose = () => {
        setConnected(false);
        if (!closedByUs) retryTimer = setTimeout(connect, 2000);
      };
      ws.onerror = () => ws.close();
      ws.onmessage = (evt) => {
        const txn = JSON.parse(evt.data);
        setTransactions((prev) => [txn, ...prev].slice(0, BUFFER_SIZE));
        if (txn.flagged) setLastFlagged(txn);
      };
    }
    connect();

    return () => {
      closedByUs = true;
      clearTimeout(retryTimer);
      ws?.close();
    };
  }, []);

  return { transactions, connected, lastFlagged };
}
