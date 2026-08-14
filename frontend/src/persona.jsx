import React from "react";

// Five demo roles across two modules, switched client-side — NOT real
// authentication. Where a server-side control actually exists (the
// compliance module's tier-1/tier-2 escalation — aci/orchestrator.py
// record_human_decision rejects a tier-1 "officer" decision on an
// already-escalated case with a real 403, regardless of what the client
// claims), login/persona-switching just lets one person demo both sides of
// that boundary without two accounts. The cybercrime module's officer
// identity is logged (every action is attributed by name in the case
// history/audit) but not itself an authorization boundary — same posture as
// a real command console where any signed-in officer can act, and
// accountability comes from the log, not a lock. Same localStorage-
// persistence pattern as the theme toggle in components.jsx.
export const PERSONAS = {
  officer: { id: "officer", role: "officer", name: "S. Compliance Officer", initials: "SC", title: "Compliance Officer", module: "compliance" },
  senior: { id: "senior", role: "senior", name: "R. Menon", initials: "RM", title: "Senior Compliance Officer · MLRO", module: "compliance" },
  nodal: { id: "nodal", role: "nodal", name: "A. Kulkarni", initials: "AK", title: "Nodal / Escalation Lead Officer", module: "cybercrime" },
  io: { id: "io", role: "io", name: "V. Sharma", initials: "VS", title: "Investigation Officer (IO)", module: "cybercrime" },
  analyst: { id: "analyst", role: "analyst", name: "N. Iyer", initials: "NI", title: "Bank Fraud / Cyber Cell Analyst", module: "cybercrime" },
};

export const MODULES = {
  compliance: { id: "compliance", label: "Compliance Unit", subtitle: "Cross-border AML investigation · GIFT IFSC" },
  cybercrime: { id: "cybercrime", label: "Cyber Crime Unit", subtitle: "Live fraud monitoring · multi-officer command" },
};

function initialsOf(name) {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

const PersonaContext = React.createContext(null);

export function PersonaProvider({ children }) {
  const [personaId, setPersonaIdRaw] = React.useState(() => localStorage.getItem("vigilo-persona") || "officer");
  const [customName, setCustomName] = React.useState(() => localStorage.getItem("vigilo-custom-name") || "");
  const [loggedIn, setLoggedIn] = React.useState(() => localStorage.getItem("vigilo-logged-in") === "true");

  React.useEffect(() => { localStorage.setItem("vigilo-persona", personaId); }, [personaId]);
  React.useEffect(() => { localStorage.setItem("vigilo-custom-name", customName); }, [customName]);
  React.useEffect(() => { localStorage.setItem("vigilo-logged-in", String(loggedIn)); }, [loggedIn]);

  const base = PERSONAS[personaId] || PERSONAS.officer;
  const persona = React.useMemo(
    () => (customName ? { ...base, name: customName, initials: initialsOf(customName) } : base),
    [base, customName]
  );

  // The login page's sign-in form: a typed name plus a chosen role.
  const login = React.useCallback((name, role) => {
    setPersonaIdRaw(PERSONAS[role] ? role : "officer");
    setCustomName(name ? name.trim() : "");
    setLoggedIn(true);
  }, []);

  // The topbar's quick role-switch, kept for mid-demo convenience — reverts
  // to that role's default name rather than carrying over a typed one, since
  // "R. Menon" shouldn't inherit whatever name the officer typed at login.
  const setPersonaId = React.useCallback((role) => {
    setPersonaIdRaw(role);
    setCustomName("");
  }, []);

  const logout = React.useCallback(() => setLoggedIn(false), []);

  const value = React.useMemo(
    () => ({ persona, setPersonaId, loggedIn, login, logout }),
    [persona, setPersonaId, loggedIn, login, logout]
  );
  return <PersonaContext.Provider value={value}>{children}</PersonaContext.Provider>;
}

export function usePersona() {
  const ctx = React.useContext(PersonaContext);
  if (!ctx) throw new Error("usePersona() must be used within a PersonaProvider");
  return ctx;
}
