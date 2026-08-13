---
name: vigilo-theme
description: >
  Apply the VIGILO design system — a professional slate/blue government-SOC visual theme with
  light/dark mode, three-font typography, severity color coding, and structured layout tokens.
  Use this skill whenever the user asks to build any UI, dashboard, web app, artifact, HTML page,
  or React component and wants the VIGILO look, SOC-style theme, slate/blue government aesthetic,
  or references this design system. Also trigger when the user says "use the VIGILO theme",
  "use my theme", "use my color scheme", "use my design system", or asks for a polished
  professional dark/light dashboard UI.
---

# VIGILO Design System

A professional slate/blue government-SOC visual theme with full light/dark mode support,
structured typography, severity-coded color semantics, and responsive layout rules.

---

## 1. Theme Tokens (CSS Custom Properties)

Set on `[data-theme="light"]` and `[data-theme="dark"]`. Light is the default.

### Surfaces & Backgrounds

| Token | Light | Dark |
|---|---|---|
| `--page` | `#f4f6f9` | `#0b131e` |
| `--surface` | `#ffffff` | `#0f172a` |
| `--sunken` | `#f8fafc` | `#142235` |
| `--raised` | `#f1f5f9` | `#1e293b` |

### Borders

| Token | Light | Dark |
|---|---|---|
| `--border` | `#e2e8f0` | `#1e324d` |
| `--hair` | `#f1f5f9` | `#1a2942` |

### Text

| Token | Light | Dark |
|---|---|---|
| `--text` | `#0f172a` | `#f8fafc` |
| `--muted` | `#64748b` | `#94a3b8` |
| `--faint` | `#94a3b8` | `#64748b` |

### Accent & Status

| Token | Light | Dark | Usage |
|---|---|---|---|
| `--accent` | `#2563eb` | `#3b82f6` | Primary actions, active nav, links |
| `--crit` | `#dc2626` | `#ef4444` | Critical / error / danger |
| `--high` | `#ea580c` | `#f97316` | High severity / warning |
| `--med` | `#d97706` | `#f59e0b` | Medium severity / caution |
| `--ok` | `#16a34a` | `#10b981` | Success / healthy / armed |

### Soft Backgrounds & Borders (for pills, badges, banners)

Every status color gets a `-soft` background and `-line` border:

```css
--crit-soft: light → #fef2f2 / dark → rgba(239,68,68,.12);
--crit-line: light → #fecaca / dark → rgba(239,68,68,.25);
--high-soft: light → #fff7ed / dark → rgba(249,115,22,.12);
--high-line: light → #fed7aa / dark → rgba(249,115,22,.25);
--med-soft:  light → #fffbeb / dark → rgba(245,158,11,.12);
--med-line:  light → #fde68a / dark → rgba(245,158,11,.25);
--ok-soft:   light → #f0fdf4 / dark → rgba(16,185,129,.12);
--ok-line:   light → #bbf7d0 / dark → rgba(16,185,129,.25);
```

### Design Principle

**Colour only where it carries meaning.** Status pills, alert badges, KPI meters, state
indicators — these get colour. Everything else is slate text on white/dark surfaces with
hairline dividers. Never decorate with colour for decoration's sake.

---

## 2. Typography — Three Fonts, Three Jobs

Import via Google Fonts:

```css
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap');
```

| Font | CSS var | Use for |
|---|---|---|
| **Space Grotesk** | `--font-display` | Headings, view titles, KPI figures, HUD readouts, hero numbers |
| **JetBrains Mono** | `--font-mono` | Code, IDs, tags, hashes, status pills, section eyebrow labels, technical metadata |
| **IBM Plex Sans** | `--font-body` | Body copy, descriptions, form labels, table cells, general prose |

```css
:root {
  --font-display: 'Space Grotesk', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
  --font-body: 'IBM Plex Sans', system-ui, sans-serif;
}
body { font-family: var(--font-body); }
h1, h2, h3, .kpi-value { font-family: var(--font-display); }
code, .tag, .pill, .mono { font-family: var(--font-mono); }
```

---

## 3. Component Patterns

### Cards
```css
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
}
```

### Status Pills / Badges
```css
.pill {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 3px 10px;
  border-radius: 6px;
}
.pill-crit { background: var(--crit-soft); color: var(--crit); border: 1px solid var(--crit-line); }
.pill-high { background: var(--high-soft); color: var(--high); border: 1px solid var(--high-line); }
.pill-med  { background: var(--med-soft);  color: var(--med);  border: 1px solid var(--med-line);  }
.pill-ok   { background: var(--ok-soft);   color: var(--ok);   border: 1px solid var(--ok-line);   }
```

### Section Eyebrows
```css
.eyebrow {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--muted);
  margin-bottom: 8px;
}
```

### KPI / Stat Figures
```css
.kpi-value {
  font-family: var(--font-display);
  font-size: 32px;
  font-weight: 700;
  color: var(--text);
}
.kpi-label {
  font-family: var(--font-mono);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--muted);
}
```

### Buttons
```css
.btn-primary {
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 8px 18px;
  font-family: var(--font-body);
  font-weight: 600;
  cursor: pointer;
}
.btn-ghost {
  background: transparent;
  color: var(--muted);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 8px 18px;
  font-family: var(--font-body);
}
```

### Tables
```css
table { width: 100%; border-collapse: collapse; }
th {
  font-family: var(--font-mono);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--muted);
  text-align: left;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
}
td {
  font-family: var(--font-body);
  padding: 12px 14px;
  border-bottom: 1px solid var(--hair);
  color: var(--text);
}
```

---

## 4. Dark / Light Toggle

Implement with a `data-theme` attribute on a root element. Default to light. Persist
choice to `localStorage`.

```js
function toggleTheme() {
  const root = document.documentElement; // or your app wrapper
  const current = root.getAttribute('data-theme') || 'light';
  const next = current === 'light' ? 'dark' : 'light';
  root.setAttribute('data-theme', next);
  localStorage.setItem('vigilo-theme', next);
}
// On load:
const saved = localStorage.getItem('vigilo-theme') || 'light';
document.documentElement.setAttribute('data-theme', saved);
```

Toggle button uses ☾ (moon) for "switch to dark" and ☀ (sun) for "switch to light".

---

## 5. Layout Rules

- **Sidebar:** 244px fixed left, background `var(--surface)`, right border `var(--border)`.
- **Header:** 64px height, sticky top, background `var(--surface)`, bottom border `var(--hair)`.
- **Content area:** fills remaining space, background `var(--page)`, padding 24px.
- **Card grids:** `display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px;`
- **Responsive:**
  - Under 1200px — sidebar collapses to icon-only (56px) or becomes a hamburger drawer.
  - Under 900px — single-column card stack, KPI strip wraps.
- Scrolling flex children need `flex: none` or they collapse.
- Panels are opaque (`var(--surface)`) and sit on `z-index: 1`.

---

## 6. How to Apply

When building any UI with this theme:

1. Set up the CSS custom properties from §1 on `[data-theme="light"]` and `[data-theme="dark"]`.
2. Import the three Google Fonts from §2.
3. Use the component patterns from §3 for cards, pills, tables, KPIs, and buttons.
4. Wire the theme toggle from §4.
5. Follow the layout skeleton from §5.
6. Remember: **colour is semantic, not decorative.** The UI should feel clean, professional,
   and government-grade — lots of white space, slate tones, hairline borders, with colour
   reserved for status and actions.
