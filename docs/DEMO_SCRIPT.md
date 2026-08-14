# Demo Run Sheet — AI Compliance Investigator

**Presenter script. Read while you click.**

Six minutes, seven steps. Every step has a **DO** (what you click) and a
**SAY** (what you say out loud).

> **Step 4 is the keystone.** If you're running short on time, cut steps 6 and
> 7 — never step 4. That's the step that wins the argument.

| | |
|---|---|
| Runtime | ~6 minutes |
| Steps | 7 |
| Keystone | Step 4 (sanctions pair) |
| Safe to cut | Steps 6–7 |

---

## Before they arrive

Do this **five minutes early**, not while someone is watching.

```bash
python scripts/start.py
```

- Browser opens on **localhost:5173**. Sign in as **Compliance Officer**, then
  log back out so you start clean on the landing page.
- **Pre-run TX-84721 and TX-66150 once.** The local model takes ~25 seconds to
  write a narrative on CPU. Running them now makes them instant later — the
  pipeline still animates for the audience.
- Check Ollama is up: the dashboard's **Local model status** card should show
  three green dots.
- Zoom the browser to **110%**. The reason chips and risk rows are small on a
  projector.

### ⚠ If the model is slow or dies mid-demo

**The demo still works.** Every score, finding, citation and evidence item is
deterministic — only the prose narrative falls back to a template.

Say it out loud if it happens. It turns a stall into a point:

> *"That's the local model running on CPU. Notice the risk score and the
> findings are already there — none of that comes from the model."*

---

## The demo

Sign in as **Compliance Officer** to begin.

### 1 · Frame the problem before showing anything — `0:00`

**DO:** Stay on the landing page. Don't click yet.

**SAY:**

> A compliance officer gets an alert that says *"high risk, 0.82."* They can't
> tell you why, can't check it, and can't defend it to a regulator. This system
> does the investigation and shows its working — **AI gathers the evidence, a
> human makes every decision.** It runs entirely on this laptop. No cloud, no
> API key.

---

### 2 · One transaction, six agents — `0:30`

**DO:** `Case queue` → `TX-84721` → `Run investigation`

**SAY:**

> One cross-border payment, ₹4.8 crore, India → UAE → Singapore. Six agents look
> at it from different angles — behaviour, entities, sanctions, regulation,
> documents, KYC. Watch the pipeline move stage to stage. **That's not a loading
> animation** — each stage is a separate agent with its own findings.

**While it runs**, point at the evidence graph on the right:

> *"Rajiv Menon directs both the sender and the beneficiary. Nobody told the
> system to look for that."*

---

### 3 · Every number traces to evidence — `1:45`

**DO:** Point at `Explainable risk`, then the `from:` line under each row.

**SAY:**

> Six weighted dimensions, and every row says which finding produced it. The
> citations are real documents — RBI, IFSCA, MAS, FATF — each with a source link
> you can open. And confidence is separate from risk: **0.84 confidence means
> the evidence is solid, not that there's an 84% chance of fraud.**

---

### 4 · ⭐ KEYSTONE — Sanctions: the match, then the near-miss — `2:30`

> **Do not cut this step.** If a judge remembers one thing, make it this pair.

**DO:** `Case queue` → `TX-66150` → open it

**SAY:**

> Screening hit. The beneficiary matches a watchlist entry at 98%. Now look at
> the score — **0.55, which is MEDIUM** — but the case is **HIGH**. A sanctions
> match isn't one more weighted input, it's a legal trigger, so it sets a floor.
> The banner says the band was raised, and the score is still shown honestly.

**DO:** `Case queue` → `TX-66151` → open it

**SAY:**

> Same customer, same corridor, same amount, **same 0.545 score**. The only
> difference is the beneficiary's name — Zenith instead of Zarnex. It scores
> 80%, below the threshold, so it comes back **clean**.
>
> *Anyone can demo a system that flags things. This is the half that matters:
> it doesn't flag the one that only looks similar.*

**Back it up with:** zero false positives across 5,000 synthetic counterparties
in the evaluation.

---

### 5 · The queue knows what's urgent — `3:45`

**DO:** `Case queue` → then click `How is this ordered?`

**SAY:**

> The sanctions case is at the top, and every case shows **why** it's in that
> position. The weights are open — a match outranks a high-risk case plus a
> breached SLA combined, because it's the one thing with a legal clock on it.

---

### 6 · Ask the case a question — `4:15`

**DO:** Open any case → `Ask this case` → click
`Why is this case at its current risk band?`

**DO:** Then type: `What is the CEO's home address?`

**SAY:**

> It answers from this case's evidence only. And when the evidence doesn't cover
> something, **it says so instead of guessing.** That refusal is the feature — a
> compliance tool that invents an answer is worse than one that admits the gap.

**Add:** Both the question and the answer go into the audit trail. What the
officer asked the system is part of how the decision got made.

---

### 7 · The human decides — and it's enforced — `5:00`

**DO:** On the case → `Escalate to senior officer`

**DO:** Persona switcher (top right) → `R. Menon` → `Escalation queue`

**SAY:**

> The AI drafts a suggestion — see the amber block, labelled *"AI suggests, not
> a decision"*. It does not pre-fill the form. Once escalated, the tier-1
> officer **cannot decide this case anymore** — the API returns a real 403. It's
> a two-person control, not a disabled button. And the whole audit trail is
> SHA-256 hash-chained: edit any past entry and every hash after it breaks.

---

## If they ask

The three questions most likely to come, and the honest answers.

### Q: Is that a real sanctions list?

**A:** No — and deliberately so. It's entirely fabricated, including the list
names. A prototype putting a real designated name next to *"MATCH — CONFIRMED"*
makes a defamatory claim about a real party. Production would drop in a licensed
feed. The agent publishes its own limitations right in the UI — no phonetic
matching, no date-of-birth corroboration, no list versioning.

### Q: Isn't the LLM making these decisions?

**A:** No. Every score, finding, citation and evidence item is deterministic
Python. The model only writes prose. Kill Ollama and re-run — you get
byte-identical results with a template narrative. There's a test that asserts
exactly that across every demo transaction.

### Q: What are the accuracy numbers?

**A:** On 5,000 synthetic transactions: **precision 0.569, recall 1.000, F1
0.726**. Tuned for recall on purpose — in AML triage a missed case costs more
than an extra review. The normal population contains deliberate near-misses; an
earlier version without them scored a meaningless 1.000. **162 tests**,
including prompt injection and tamper detection.

---

## If you have extra time

Only if they're engaged and the clock allows.

- **TX-31204** — a completely clean transaction that still reaches review,
  purely because the customer's own risk rating is HIGH. Shows the Risk-Based
  Approach in isolation.
- **New transaction** — submit one live. Proves nothing is staged.
- **Cyber Crime Unit** — switch persona for a second console: live WebSocket
  transaction feed, mule-network layering flow, geographic heat map.
- **Detection rules** — every rule the system runs, with its real threshold,
  read live from config.

---

## Cheat sheet — the numbers

| Fact | Value |
|---|---|
| Demo transactions | TX-84721 (multi-signal), TX-66150 (sanctions hit), TX-66151 (near-miss control), TX-31204 (customer-risk only) |
| Sanctions pair score | Both **0.545** — only the name differs |
| Match vs near-miss | **98%** (floored to HIGH) vs **80%** (clean) |
| Evaluation | 5,000 transactions · P 0.569 · R 1.000 · F1 0.726 |
| Sanctions false positives | **0** across 5,000 counterparties |
| Tests | **162** |
| Regulatory documents | 11 real, source-linked (RBI, IFSCA, CBUAE, MAS, FATF) |
| Local model | `qwen3:4b` via Ollama — no cloud, no API key |
| Audit trail | SHA-256 hash-chained, tamper-evident |

---

*All data synthetic · watchlist fabricated · runs offline on local hardware*
