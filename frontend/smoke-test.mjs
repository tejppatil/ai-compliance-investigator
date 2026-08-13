/**
 * UI smoke test — drives the real console in a real browser.
 *
 *   npm run smoke                    # uses installed Chrome/Edge
 *   CHROME_PATH=/path/to/chrome npm run smoke
 *
 * Requires the API and dev server to be running (python scripts/start.py).
 * Screenshots land in frontend/smoke-shots/ (gitignored).
 *
 * Uses playwright-core against an already-installed browser rather than
 * `playwright`, so no ~150MB browser download is needed to verify the UI.
 */
import { chromium } from "playwright-core";
import { existsSync, mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";

// fileURLToPath, not .pathname — the latter leaves %20 in paths like
// "D:/Young Builders" and the screenshots end up somewhere unexpected.
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
const page = await (await browser.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
page.on("pageerror", (e) => errors.push("PAGEERROR: " + e.message));

async function step(name, fn) {
  try { await fn(); console.log(`  OK   ${name}`); }
  catch (e) { failed++; console.log(`  FAIL ${name}: ${e.message.split("\n")[0]}`); }
}

console.log(`Smoke-testing ${WEB}\n`);

await step("dashboard loads with live KPIs", async () => {
  await page.goto(WEB, { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForSelector("text=Total transactions", { timeout: 20000 });
});
await page.screenshot({ path: `${SHOTS}/01-dashboard.png` });

await step("case queue lists transactions", async () => {
  await page.click('button:has-text("Case queue")');
  await page.waitForSelector("text=TX-84721", { timeout: 15000 });
});

await step("open the high-risk case", async () => {
  await page.click("text=TX-84721");
  // Either state is valid: a fresh case shows the run button, an already
  // investigated one goes straight to the risk panel.
  await Promise.race([
    page.waitForSelector('button:has-text("Run investigation")', { timeout: 15000 }),
    page.waitForSelector("text=Explainable risk", { timeout: 15000 }),
  ]);
});

await step("run the investigation (local LLM may take ~40s)", async () => {
  const needsRun = await page.locator('button:has-text("Run investigation")').count();
  if (needsRun) await page.click('button:has-text("Run investigation")');
  await page.waitForSelector("text=Explainable risk", { timeout: 150000 });
});
await page.screenshot({ path: `${SHOTS}/02-investigation.png`, fullPage: true });

await step("all four agents reported", async () => {
  for (const a of ["Transaction Intelligence", "Entity Intelligence", "Compliance Intelligence", "Document Analysis"]) {
    await page.waitForSelector(`text=${a}`, { timeout: 10000 });
  }
});

await step("entity relationship detected", async () => {
  await page.waitForSelector("text=Common director", { timeout: 10000 });
});

await step("evidence graph rendered", async () => {
  await page.waitForSelector("text=Evidence graph", { timeout: 10000 });
  if ((await page.locator("svg").count()) === 0) throw new Error("no graph svg");
});

await step("human decision is recordable", async () => {
  await page.fill("textarea", "Smoke test decision.");
  await page.click('button:has-text("Escalate to senior officer")');
  await page.waitForSelector("text=recorded", { timeout: 15000 });
});
await page.screenshot({ path: `${SHOTS}/03-decision.png`, fullPage: true });

await step("audit trail captured the human action", async () => {
  await page.waitForSelector("text=Compliance officer decision", { timeout: 10000 });
});

await step("regulatory KB shows real sourced documents", async () => {
  await page.click('button:has-text("Regulatory KB")');
  await page.waitForSelector("text=MAS Notice 626", { timeout: 10000 });
});
await page.screenshot({ path: `${SHOTS}/04-regulatory.png`, fullPage: true });

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
