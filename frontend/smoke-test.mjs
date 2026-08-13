/**
 * UI smoke test — drives the real console in a real browser.
 *
 *   npm run smoke                    # uses installed Chrome/Edge
 *   CHROME_PATH=/path/to/chrome npm run smoke
 *
 * Requires the API and dev server to be running (python scripts/start.py),
 * against a FRESH database — this walks through login, the RBA landing page,
 * the live pipeline diagram, a brand-new submitted transaction, escalation,
 * and the tamper-evident audit badge in one continuous run.
 * Screenshots land in frontend/smoke-shots/ (gitignored).
 *
 * Uses playwright-core against an already-installed browser rather than
 * `playwright`, so no ~150MB browser download is needed to verify the UI.
 */
import { chromium } from "playwright-core";
import { existsSync, mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";

const SHOTS = fileURLToPath(new URL("./smoke-shots/", import.meta.url));
if (!existsSync(SHOTS)) mkdirSync(SHOTS, { recursive: true });

const WEB = process.env.WEB_URL || "http://localhost:5173";
const CHROME_CANDIDATES = [
  process.env.CHROME_PATH,
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  "/usr/bin/google-chrome",
  "/usr/bin/chromium",
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
].filter(Boolean);

const executablePath = CHROME_CANDIDATES.find((p) => existsSync(p));
if (!executablePath) {
  console.error("No Chrome/Edge found. Set CHROME_PATH to your browser binary.");
  process.exit(1);
}

const errors = [];
let failed = 0;

const browser = await chromium.launch({ executablePath, args: ["--no-sandbox"] });
const page = await (await browser.newContext({ viewport: { width: 1440, height: 950 } })).newPage();
page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
page.on("pageerror", (e) => errors.push("PAGEERROR: " + e.message));

async function step(name, fn) {
  try { await fn(); console.log(`  OK   ${name}`); }
  catch (e) { failed++; console.log(`  FAIL ${name}: ${e.message.split("\n")[0]}`); }
}

console.log(`Smoke-testing ${WEB}\n`);

// ── Login + RBA landing page ────────────────────────────────────────────────
await step("fresh load lands on the RBA + login page (not the app shell)", async () => {
  await page.goto(WEB, { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForSelector("text=Risk isn't one number from nowhere", { timeout: 20000 });
});

await step("RBA weight chart, policy table, and FATF R.1 citation render from real API data", async () => {
  await page.waitForSelector("text=The six dimensions", { timeout: 15000 });
  await page.waitForSelector("text=Recommended action by risk band", { timeout: 10000 });
  await page.waitForSelector("text=FATF Recommendation 1", { timeout: 10000 });
  if ((await page.locator("svg.recharts-surface").count()) === 0) throw new Error("no recharts chart rendered");
});
await page.screenshot({ path: `${SHOTS}/01-rba-landing.png`, fullPage: true });

await step("sign in as officer", async () => {
  await page.fill('input[placeholder="S. Compliance Officer"]', "Smoke Test Officer");
  await page.click('button:has-text("Compliance Officer")');
  await page.click('button:has-text("Sign in")');
  await page.waitForSelector("text=Total transactions", { timeout: 10000 });
});

// ── New sidebar pages ────────────────────────────────────────────────────────
await step("How it works page renders the static pipeline diagram", async () => {
  await page.click('button:has-text("How it works")');
  await page.waitForSelector("text=KYC Completeness", { timeout: 10000 });
  await page.waitForSelector("text=Why this shape", { timeout: 5000 });
});

await step("Detection rules page lists the real rule catalogue", async () => {
  await page.click('button:has-text("Detection rules")');
  await page.waitForSelector("text=amount_anomaly", { timeout: 10000 });
  await page.waitForSelector("text=kyc_date_inconsistency", { timeout: 5000 });
});
await page.screenshot({ path: `${SHOTS}/02-rules.png`, fullPage: true });

// ── Submit a brand-new transaction and watch the live pipeline ─────────────
await step("submit a new transaction via the intake form", async () => {
  await page.click('button:has-text("New transaction")');
  await page.waitForSelector("select", { timeout: 10000 });
  await page.fill('input[placeholder="e.g. Gulf Trading Partners LLC"]', "Smoke Test Trading LLC");
  await page.fill('input[placeholder="e.g. services"]', "services");
  await page.click('button:has-text("Submit & investigate")');
  await Promise.race([
    page.waitForSelector('button:has-text("Run investigation")', { timeout: 15000 }),
    page.waitForSelector("text=Explainable risk", { timeout: 15000 }),
  ]);
});

await step("run the investigation and watch the live pipeline complete", async () => {
  const needsRun = await page.locator('button:has-text("Run investigation")').count();
  if (needsRun) await page.click('button:has-text("Run investigation")');
  await page.waitForSelector("text=Explainable risk", { timeout: 150000 });
  await page.waitForSelector("text=Pipeline — proof it moves stage to stage", { timeout: 10000 });
  await page.waitForSelector("text=KYC Completeness", { timeout: 10000 });
});
await page.screenshot({ path: `${SHOTS}/03-new-transaction-investigated.png`, fullPage: true });

await step("audit trail shows the hash-chain-verified badge", async () => {
  await page.waitForSelector("text=Hash chain verified", { timeout: 15000 });
});

await step("investigation timeline and evidence graph render", async () => {
  await page.waitForSelector("text=how it happened", { timeout: 10000 });
  if ((await page.locator("svg").count()) === 0) throw new Error("no evidence graph svg");
});

// ── Two-tier escalation control (still the core mechanism) ─────────────────
await step("escalate the case as officer", async () => {
  await page.fill("textarea", "Escalating for smoke test.");
  await page.click('button:has-text("Escalate to senior officer")');
  await page.waitForSelector("text=Escalated — awaiting senior review", { timeout: 15000 });
});

await step("switch to Senior Compliance Officer and resolve via the Escalation Queue", async () => {
  await page.click('button:has-text("Smoke Test Officer")');
  await page.waitForSelector("text=DEMO PERSONA SWITCHER", { timeout: 5000 });
  await page.click("text=R. Menon");
  await page.waitForTimeout(300);
  await page.click('button:has-text("Escalation queue")');
  await page.waitForSelector("text=Review →", { timeout: 10000 });
  await page.click("text=Review →");
  await page.waitForSelector("text=Senior review — decision required", { timeout: 10000 });
  await page.fill("textarea", "Reviewed and approved.");
  await page.click('button:has-text("Approve AI assessment")');
  await page.waitForSelector("text=Escalation resolved", { timeout: 15000 });
});

// ── Dashboard reflects everything, incl. the new network-insights panel ────
await step("dashboard shows network insights and updated KPIs", async () => {
  await page.click('button:has-text("Dashboard")');
  await page.waitForSelector("text=Network insights", { timeout: 10000 });
});
await page.screenshot({ path: `${SHOTS}/04-dashboard-final.png`, fullPage: true });

await step("regulatory KB still shows real sourced documents incl. FATF R.1", async () => {
  await page.click('button:has-text("Regulatory KB")');
  await page.waitForSelector("text=MAS Notice 626", { timeout: 10000 });
  await page.waitForSelector("text=Risk-Based Approach", { timeout: 5000 });
});

await step("dark mode toggle", async () => {
  await page.click('button[title="Toggle theme"]');
  await page.waitForTimeout(500);
});
await page.screenshot({ path: `${SHOTS}/05-dark.png` });

await step("log out returns to the RBA + login page", async () => {
  await page.click('button:has-text("R. Menon")');
  await page.waitForSelector("text=Log out", { timeout: 5000 });
  await page.click("text=Log out");
  await page.waitForSelector("text=Risk isn't one number from nowhere", { timeout: 10000 });
});

await browser.close();

console.log(`\nScreenshots: ${SHOTS}`);
if (errors.length) {
  console.log("\nConsole errors:");
  errors.forEach((e) => console.log("  " + e));
}
if (failed || errors.length) {
  console.log(`\nFAILED (${failed} step(s), ${errors.length} console error(s))`);
  process.exit(1);
}
console.log("\nAll steps passed, no console errors.");
