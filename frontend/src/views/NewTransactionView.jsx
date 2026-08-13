import React from "react";
import { Card, Pill } from "../components.jsx";
import { api } from "../api.js";
import { ErrorBanner } from "./DashboardView.jsx";

const COUNTRIES = ["UAE", "Singapore", "India", "United Kingdom", "Hong Kong"];

export default function NewTransactionView({ openCase }) {
  const [customers, setCustomers] = React.useState(null);
  const [error, setError] = React.useState(null);
  const [submitting, setSubmitting] = React.useState(false);
  const [form, setForm] = React.useState({
    customer_id: "", amount: 4_500_000, beneficiary_name: "", beneficiary_country: "UAE",
    destination_country: "UAE", purpose: "Consulting services", document_narrative: "", document_amount: "",
  });

  React.useEffect(() => {
    api.listCustomers().then((cs) => { setCustomers(cs); setForm((f) => ({ ...f, customer_id: cs[0]?.customer_id || "" })); })
      .catch((e) => setError(e.message));
  }, []);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  async function submit(e) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const { transaction_id } = await api.createTransaction({
        customer_id: form.customer_id, amount: Number(form.amount),
        beneficiary_name: form.beneficiary_name || "New Counterparty Trading LLC",
        beneficiary_country: form.beneficiary_country, destination_country: form.destination_country,
        purpose: form.purpose, document_narrative: form.document_narrative || undefined,
        document_amount: form.document_amount ? Number(form.document_amount) : undefined,
      });
      openCase(transaction_id);
    } catch (e2) {
      setError(e2.message);
    } finally {
      setSubmitting(false);
    }
  }

  if (error) return <ErrorBanner message={error} />;
  if (!customers) return <div style={{ color: "var(--muted)", fontSize: 13 }}>Loading…</div>;

  const selected = customers.find((c) => c.customer_id === form.customer_id);

  return (
    <div style={{ maxWidth: 560 }}>
      <p style={{ color: "var(--muted)", fontSize: 13, marginTop: 0, marginBottom: 18, lineHeight: 1.6 }}>
        Submit a transaction that doesn't exist in the fixed demo queue — it flows through the
        identical pipeline, live. The beneficiary is created fresh with today's registration date,
        so a genuine <code className="mono">new_counterparty</code> signal (not scripted) is a real
        possibility depending on what you enter.
      </p>
      <Card>
        <form onSubmit={submit}>
          <Field label="Sending customer (existing)">
            <select value={form.customer_id} onChange={set("customer_id")} style={{ width: "100%" }}>
              {customers.map((c) => <option key={c.customer_id} value={c.customer_id}>{c.name} ({c.country})</option>)}
            </select>
            {selected && selected.risk_profile !== "standard" && (
              <div style={{ marginTop: 6 }}><Pill sev={selected.risk_profile === "high" ? "high" : "medium"}>{selected.risk_profile.toUpperCase()} RISK CUSTOMER</Pill></div>
            )}
          </Field>
          <Field label="Amount (INR)"><input type="number" min="1" value={form.amount} onChange={set("amount")} style={{ width: "100%" }} /></Field>
          <Field label="Beneficiary name (new entity)"><input type="text" value={form.beneficiary_name} onChange={set("beneficiary_name")} placeholder="e.g. Gulf Trading Partners LLC" style={{ width: "100%" }} /></Field>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <Field label="Beneficiary country">
              <select value={form.beneficiary_country} onChange={set("beneficiary_country")} style={{ width: "100%" }}>
                {COUNTRIES.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </Field>
            <Field label="Destination country">
              <select value={form.destination_country} onChange={set("destination_country")} style={{ width: "100%" }}>
                {COUNTRIES.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </Field>
          </div>
          <Field label="Purpose"><input type="text" value={form.purpose} onChange={set("purpose")} style={{ width: "100%" }} /></Field>
          <Field label="Invoice narrative (optional)"><input type="text" value={form.document_narrative} onChange={set("document_narrative")} placeholder="e.g. services" style={{ width: "100%" }} /></Field>
          <Field label="Invoice amount (optional, defaults to transaction amount)"><input type="number" value={form.document_amount} onChange={set("document_amount")} style={{ width: "100%" }} /></Field>
          <button type="submit" className="btn-primary" disabled={submitting} style={{ width: "100%", marginTop: 6 }}>
            {submitting ? "Submitting…" : "Submit & investigate"}
          </button>
        </form>
      </Card>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <label style={{ fontSize: 11, color: "var(--muted)", display: "block", marginBottom: 4 }}>{label}</label>
      {children}
    </div>
  );
}
