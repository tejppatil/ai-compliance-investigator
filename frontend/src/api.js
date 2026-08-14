// Thin fetch wrapper over the FastAPI backend (aci/api/app.py). Every value
// rendered by this console comes from one of these calls — nothing here is
// hardcoded demo data computed in the browser.
// Port 8077, not 8000: the Ollama desktop app binds 8000 on Windows, and this
// project requires Ollama, so 8000 is a guaranteed collision here.
const BASE = import.meta.env.VITE_API_BASE || "http://localhost:8077";

async function request(path, options) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch { /* not JSON */ }
    throw new Error(`${res.status} ${detail}`);
  }
  return res.status === 204 ? null : res.json();
}

export const api = {
  status: () => request("/api/status"),
  dashboard: () => request("/api/dashboard"),
  listTransactions: () => request("/api/transactions"),
  listCustomers: () => request("/api/customers"),
  listInvestigations: () => request("/api/investigations"),
  createInvestigation: (transaction_id) =>
    request("/api/investigations", { method: "POST", body: JSON.stringify({ transaction_id }) }),
  getCase: (caseId) => request(`/api/investigations/${caseId}`),
  getAudit: (caseId) => request(`/api/audit/${caseId}`),
  recentAudit: (limit = 8) => request(`/api/audit?limit=${limit}`),
  review: (caseId, decision, note, { actor = "compliance.officer", role = "officer" } = {}) =>
    request(`/api/investigations/${caseId}/review`, {
      method: "POST",
      body: JSON.stringify({ decision, note, actor, role }),
    }),
  listRegulations: () => request("/api/regulations"),
  searchRegulations: (q, k = 5) => request(`/api/regulations/search?q=${encodeURIComponent(q)}&k=${k}`),
  listEscalations: () => request("/api/escalations"),
  queue: () => request("/api/queue"),
  sanctions: (caseId) => request(`/api/sanctions/${caseId}`),
  askCase: (caseId, question) =>
    request(`/api/investigations/${caseId}/ask`, { method: "POST", body: JSON.stringify({ question }) }),
  networkInsights: () => request("/api/network-insights"),
  riskMethodology: () => request("/api/risk-methodology"),
  rules: () => request("/api/rules"),
  verifyAudit: (caseId) => request(`/api/audit/${caseId}/verify`),
  createTransaction: (payload) =>
    request("/api/transactions", { method: "POST", body: JSON.stringify(payload) }),

  // ── Cyber Crime module (aci/api/cybercrime_routes.py) ──────────────────
  cyberOfficers: () => request("/api/cyber/officers"),
  cyberCases: () => request("/api/cyber/cases"),
  cyberCase: (caseId) => request(`/api/cyber/cases/${caseId}`),
  cyberEscalate: (caseId, officer_name, note = "") =>
    request(`/api/cyber/cases/${caseId}/escalate`, { method: "POST", body: JSON.stringify({ officer_name, note }) }),
  cyberTransfer: (caseId, new_officer_id, actor_name) =>
    request(`/api/cyber/cases/${caseId}/transfer`, { method: "POST", body: JSON.stringify({ new_officer_id, actor_name }) }),
  cyberFreeze: (txId, officer_name) =>
    request(`/api/cyber/transactions/${txId}/freeze`, { method: "POST", body: JSON.stringify({ officer_name }) }),
  cyberFreezeHop: (caseId, hop_index, officer_name) =>
    request(`/api/cyber/cases/${caseId}/freeze-hop`, { method: "POST", body: JSON.stringify({ hop_index, officer_name }) }),
  cyberRecentTransactions: (limit = 50) => request(`/api/cyber/transactions/recent?limit=${limit}`),
  cyberGeoIncidents: (params = {}) => {
    const q = new URLSearchParams(Object.entries(params).filter(([, v]) => v));
    const qs = q.toString();
    return request(`/api/cyber/geo-incidents${qs ? `?${qs}` : ""}`);
  },
  cyberGraph: (caseId) => request(`/api/cyber/graph/${caseId}`),
};

export const CYBER_WS_URL = BASE.replace(/^http/, "ws") + "/ws/cyber/transactions";

export const caseIdFor = (transactionId) => `CASE-${transactionId.split("-").pop()}`;
