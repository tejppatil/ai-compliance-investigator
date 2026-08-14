import React from "react";
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { Card, Eyebrow } from "../components.jsx";
import { api } from "../api.js";
import { CyberPill } from "./shared.jsx";

const CRIME_TYPES = ["Phishing", "Mule Network", "Ransomware", "Investment Fraud", "Account Takeover"];
const SEVERITIES = ["low", "medium", "high", "critical"];
const TIMEFRAMES = [
  { label: "24h", hours: 24 },
  { label: "7d", hours: 24 * 7 },
  { label: "30d", hours: 24 * 30 },
  { label: "All", hours: null },
];

const SEV_COLOR = { critical: "#dc2626", high: "#ea580c", medium: "#d97706", low: "#16a34a" };
const SEV_RADIUS = { critical: 14, high: 11, medium: 8, low: 6 };

// NOTE — the ONLY part of this project that reaches the public internet at
// runtime: basemap tiles come from CARTO's CDN. Everything else (the
// compliance module's LLM, embeddings, retrieval, database, and this
// module's entire live feed and rule engine) runs on localhost, and the
// offline test covers those. Offline, Leaflet simply renders blank tiles —
// the incident markers, filters, and all counts below still work, because
// they come from our own API. Swapping in self-hosted tiles would remove
// even this, at the cost of shipping a tile pack.
//
// Leaflet caches tile layers per theme; forcing a remount on theme change
// would reset the user's pan/zoom, so instead the tile layer URL swaps and
// Leaflet handles it in place.
function ThemeAwareTiles() {
  const [dark, setDark] = React.useState(
    () => document.documentElement.getAttribute("data-theme") === "dark"
  );
  React.useEffect(() => {
    const obs = new MutationObserver(() =>
      setDark(document.documentElement.getAttribute("data-theme") === "dark")
    );
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => obs.disconnect();
  }, []);
  return (
    <TileLayer
      key={dark ? "dark" : "light"}
      url={dark
        ? "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        : "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"}
      attribution='&copy; OpenStreetMap contributors &copy; CARTO'
    />
  );
}

export default function HeatMapView() {
  const [incidents, setIncidents] = React.useState(null);
  const [error, setError] = React.useState(null);
  const [crimeType, setCrimeType] = React.useState("");
  const [severity, setSeverity] = React.useState("");
  const [hours, setHours] = React.useState(null);

  React.useEffect(() => {
    api.cyberGeoIncidents({ crime_type: crimeType, severity, hours })
      .then(setIncidents)
      .catch((e) => setError(e.message));
  }, [crimeType, severity, hours]);

  const bySeverity = React.useMemo(() => {
    const counts = { critical: 0, high: 0, medium: 0, low: 0 };
    for (const i of incidents || []) counts[i.severity] = (counts[i.severity] || 0) + 1;
    return counts;
  }, [incidents]);

  const topCities = React.useMemo(() => {
    const counts = new Map();
    for (const i of incidents || []) counts.set(i.city, (counts.get(i.city) || 0) + 1);
    return [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 6);
  }, [incidents]);

  if (error) return <div className="card" style={{ color: "var(--crit)", fontSize: 13 }}>{error}</div>;

  return (
    <div>
      <p style={{ color: "var(--muted)", fontSize: 13, marginTop: 0, marginBottom: 14, maxWidth: 700, lineHeight: 1.55 }}>
        Cyber crime and financial fraud intensity, clustered from simulated 1930 helpline reports,
        flagged bank-transfer cash-out locations, and OSINT/news incident feeds. Marker size and
        colour track severity.
      </p>

      <Card style={{ marginBottom: 14 }}>
        <div style={{ display: "flex", gap: 18, flexWrap: "wrap", alignItems: "center" }}>
          <FilterGroup label="Timeframe">
            {TIMEFRAMES.map((tf) => (
              <Chip key={tf.label} on={hours === tf.hours} onClick={() => setHours(tf.hours)}>{tf.label}</Chip>
            ))}
          </FilterGroup>
          <FilterGroup label="Crime type">
            <Chip on={crimeType === ""} onClick={() => setCrimeType("")}>All</Chip>
            {CRIME_TYPES.map((c) => (
              <Chip key={c} on={crimeType === c} onClick={() => setCrimeType(c)}>{c}</Chip>
            ))}
          </FilterGroup>
          <FilterGroup label="Severity">
            <Chip on={severity === ""} onClick={() => setSeverity("")}>All</Chip>
            {SEVERITIES.map((s) => (
              <Chip key={s} on={severity === s} onClick={() => setSeverity(s)}>{s}</Chip>
            ))}
          </FilterGroup>
        </div>
      </Card>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 260px", gap: 14 }}>
        <Card style={{ padding: 0, overflow: "hidden" }}>
          <div style={{ height: 520 }}>
            <MapContainer center={[22.9734, 78.6569]} zoom={5} style={{ height: "100%", width: "100%" }} scrollWheelZoom>
              <ThemeAwareTiles />
              {(incidents || []).map((i) => (
                <CircleMarker key={i.incident_id} center={[i.lat, i.lng]} radius={SEV_RADIUS[i.severity] || 6}
                  pathOptions={{ color: SEV_COLOR[i.severity], fillColor: SEV_COLOR[i.severity], fillOpacity: 0.45, weight: 1.5 }}>
                  <Popup>
                    <div style={{ fontSize: 12, minWidth: 180 }}>
                      <b>{i.crime_type}</b> · {i.severity.toUpperCase()}<br />
                      {i.city}, {i.state}<br />
                      <span style={{ color: "#666" }}>{i.source}</span><br />
                      <span style={{ color: "#666", fontSize: 11 }}>{new Date(i.reported_at).toLocaleString()}</span>
                    </div>
                  </Popup>
                </CircleMarker>
              ))}
            </MapContainer>
          </div>
        </Card>

        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <Card>
            <Eyebrow>Matching incidents</Eyebrow>
            <div className="kpi-value">{incidents ? incidents.length : "…"}</div>
          </Card>
          <Card>
            <Eyebrow>By severity</Eyebrow>
            {SEVERITIES.slice().reverse().map((s) => (
              <div key={s} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "4px 0" }}>
                <CyberPill severity={s} />
                <span className="mono" style={{ fontSize: 12 }}>{bySeverity[s] || 0}</span>
              </div>
            ))}
          </Card>
          <Card>
            <Eyebrow>Top hotspots</Eyebrow>
            {topCities.length === 0
              ? <div style={{ fontSize: 12, color: "var(--muted)" }}>No incidents match these filters.</div>
              : topCities.map(([city, n]) => (
                <div key={city} style={{ display: "flex", justifyContent: "space-between", padding: "4px 0", fontSize: 12 }}>
                  <span style={{ color: "var(--muted)" }}>{city}</span>
                  <span className="mono">{n}</span>
                </div>
              ))}
          </Card>
        </div>
      </div>
    </div>
  );
}

function FilterGroup({ label, children }) {
  return (
    <div>
      <div className="mono" style={{ fontSize: 9.5, color: "var(--faint)", textTransform: "uppercase", marginBottom: 5 }}>{label}</div>
      <div style={{ display: "flex", gap: 5, flexWrap: "wrap" }}>{children}</div>
    </div>
  );
}

function Chip({ on, onClick, children }) {
  return (
    <button onClick={onClick} style={{ padding: "4px 10px", borderRadius: 14, cursor: "pointer", fontSize: 11,
      border: `1px solid ${on ? "var(--accent)" : "var(--border)"}`,
      background: on ? "var(--accent)" : "transparent", color: on ? "#fff" : "var(--muted)" }}>
      {children}
    </button>
  );
}
