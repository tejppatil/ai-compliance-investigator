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
  networkInsights: () => request("/api/network-insights"),
  riskMethodology: () => request("/api/risk-methodology"),
  rules: () => request("/api/rules"),
  verifyAudit: (caseId) => request(`/api/audit/${caseId}/verify`),
  createTransaction: (payload) =>
    request("/api/transactions", { method: "POST", body: JSON.stringify(payload) }),
};

export const caseIdFor = (transactionId) => `CASE-${transactionId.split("-").pop()}`;
