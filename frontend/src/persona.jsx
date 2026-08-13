import React from "react";

// Two demo roles, switched client-side — NOT real authentication. The server
// enforces the actual control (aci/orchestrator.py record_human_decision
// rejects a tier-1 "officer" decision on an already-escalated case with a
// real 403, regardless of what the client claims); login/persona-switching
// just lets one person demo both sides of that boundary without two
// accounts. Same localStorage-persistence pattern as the theme toggle in
// components.jsx.
export const PERSONAS = {
  officer: { id: "officer", role: "officer", name: "S. Compliance Officer", initials: "SC", title: "Compliance Officer" },
  senior: { id: "senior", role: "senior", name: "R. Menon", initials: "RM", title: "Senior Compliance Officer · MLRO" },
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
