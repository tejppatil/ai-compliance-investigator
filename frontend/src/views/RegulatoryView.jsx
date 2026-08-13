import React from "react";
import { Card } from "../components.jsx";
import { api } from "../api.js";
import { ErrorBanner } from "./DashboardView.jsx";

export default function RegulatoryView() {
  const [kb, setKb] = React.useState(null);
  const [q, setQ] = React.useState("");
  const [results, setResults] = React.useState(null);
  const [error, setError] = React.useState(null);

  React.useEffect(() => { api.listRegulations().then(setKb).catch((e) => setError(e.message)); }, []);

  async function search(e) {
    e.preventDefault();
    if (!q.trim()) { setResults(null); return; }
    try { setResults(await api.searchRegulations(q)); } catch (e) { setError(e.message); }
  }

  if (error) return <ErrorBanner message={error} />;
  const rows = results ?? kb;

  return (
    <div>
      <div className="card" style={{ background: "var(--med-soft)", border: "1px solid var(--med-line)", color: "var(--med)", fontSize: 12.5, lineHeight: 1.5, marginBottom: 18 }}>
        Every entry below is a real, publicly issued regulatory document, verified against the regulator's own
        site (or cross-checked against independent legal reporting where the regulator blocked automated
        fetches) — see each entry's source link. Summaries are this project's own paraphrase, not quoted statute
        text. Nothing here is invented.
      </div>
      <form onSubmit={search} style={{ marginBottom: 16, display: "flex", gap: 8 }}>
        <input type="text" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search the knowledge base (e.g. 'beneficial ownership high value')"
          style={{ flex: 1 }} />
        <button className="btn-primary" type="submit">Search</button>
        {results && <button className="btn-ghost" type="button" onClick={() => { setResults(null); setQ(""); }}>Clear</button>}
      </form>
      {!rows ? (
        <div style={{ color: "var(--muted)", fontSize: 13 }}>Loading…</div>
      ) : rows.length === 0 ? (
        <div style={{ color: "var(--muted)", fontSize: 13 }}>Insufficient information in the configured regulatory knowledge base for that query.</div>
      ) : (
        <Card style={{ padding: 0 }}>
          {rows.map((r, i) => (
            <div key={r.id} style={{ padding: 16, borderBottom: i < rows.length - 1 ? "1px solid var(--hair)" : "none" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 12 }}>
                <div style={{ fontSize: 13.5, fontWeight: 600 }}>{r.title}</div>
                <span className="mono" style={{ fontSize: 10.5, color: "var(--accent)", flexShrink: 0 }}>{r.id}</span>
              </div>
              <div className="mono" style={{ fontSize: 10, color: "var(--faint)", margin: "3px 0 7px" }}>
                {r.jurisdiction} · {r.section} · {r.regulator}
                {r.publication_date && ` · ${r.publication_date}`}
              </div>
              <div style={{ fontSize: 12.5, color: "var(--muted)", lineHeight: 1.55 }}>{r.summary}</div>
              {r.why && <div style={{ fontSize: 11.5, color: "var(--text)", marginTop: 6 }}><b>Why relevant:</b> {r.why}</div>}
              <div style={{ display: "flex", gap: 10, marginTop: 8, alignItems: "center" }}>
                {r.tags && r.tags.map((t) => <span key={t} className="mono" style={{ fontSize: 9.5, color: "var(--faint)", background: "var(--raised)", padding: "2px 7px", borderRadius: 4 }}>{t}</span>)}
                {r.source_url && <a href={r.source_url} target="_blank" rel="noreferrer" style={{ fontSize: 10.5, color: "var(--accent)", marginLeft: "auto" }}>source ↗</a>}
              </div>
            </div>
          ))}
        </Card>
      )}
    </div>
  );
}
