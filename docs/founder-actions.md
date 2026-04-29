# Founder action items — Naveen

Tracker for things only Naveen can do (decisions, signups, KYC, name reservations, etc.). The CEO/agent maintains this file; tick items off as they're done. Items added here only when execution is blocked on a real-world action.

Last updated: 2026-04-29

---

## Pending

### P0 — blocking the next phase of execution

- [ ] **Reserve handles & domains** _(15 min, $20)_
  - Check Instagram availability: `@hellonila`, `@nila.chennai`, `@nila.tanglish` — reply with which return "user not found"
  - Check Telegram bot availability: `@NilaChat_bot`, `@AskNila_bot`, `@TalkToNila_bot`
  - Once chosen: register the IG handle (just create the account, leave private), reserve the Telegram bot via @BotFather, buy `nila.app` + `nila.in` from Namecheap or Cloudflare Registrar
  - **Why now:** names get squatted overnight in this category. Reserving costs nothing in time but everything if lost.
  - **Deadline:** within 7 days

- [x] ~~**Confirm decision #5 — ethical red lines** — agreed 2026-04-29~~

- [ ] **Tell me credit expiry dates** _(10 min, in your inbox)_
  - AWS $10K — issue date / expiry date?
  - Azure $10K — issue date / expiry date?
  - OpenAI $2.5K — issue date / expiry date?
  - Grok $2.5K — issue date / expiry date?
  - Deepgram $15K — issue date / expiry date?
  - **Why:** credits expiring in <4 months change our sequencing (we'd front-load that vendor's usage).
  - **Deadline:** within 3 days

- [ ] **Create AWS IAM user `nila-deploy` and share credentials** _(10 min)_
  - I'll write a step-by-step doc with the exact IAM policy JSON in my next reply once you say go
  - Programmatic access only — no console login. You can revoke any time.
  - **Why:** unblocks staging environment setup this weekend; needed before Saturday's memory work
  - **Deadline:** before Saturday

- [ ] **Review revised system prompt (prompts.py)** _(15 min)_
  - Tomorrow morning, open `backend/prompts.py` and read it end to end
  - This is the single most important file in the product — Nila's brain. Everything else serves this.
  - Reply with any tone tweaks, hard-refusal additions, or character adjustments you want
  - **Why:** I won't wire this into `main.py` until you've signed off. Don't want to ship a Nila that doesn't sound like Nila.
  - **Deadline:** by Thursday midday (so I can build the safety layer on top of an approved prompt)

### P1 — needed before week 2 (paywall/payments week)

- [ ] **Udyam (MSME) registration as "Nila Labs"** _(10 min, free)_
  - Go to [udyamregistration.gov.in](https://udyamregistration.gov.in/)
  - Enter Aadhaar + PAN, business name "Nila Labs", classify as "Services — IT/Software"
  - Save the Udyam certificate PDF
  - **Why:** required for Razorpay to display "Nila" on checkout instead of your personal name.
  - **Deadline:** by end of week 2

- [ ] **Open / designate a current account in "Naveen Kumar Ezhumalai trading as Nila Labs"** _(2-3 days, ~₹0)_
  - ICICI / HDFC / Kotak all do this for sole props
  - Bring: Aadhaar, PAN, Udyam certificate, address proof
  - Or: convert your existing savings account if your bank allows
  - **Why:** Razorpay payouts land here. Bank statement entries on user side will show "Nila" merchant descriptor.
  - **Deadline:** by end of week 2

- [ ] **Razorpay account onboarding** _(1 day, free)_
  - Create Razorpay account, do business KYC with Udyam + bank account + PAN
  - Set business display name to **"Nila"**, merchant descriptor to **"NILACHAT"**
  - **Why:** payments rail.
  - **Deadline:** end of week 2

### P2 — needed before week 4-5 (paywall going live)

- [ ] **1-hour call with Indian tech lawyer** _(1 hr + ₹15-25K)_
  - Shortlist: Ikigai Law, NovoJuris, Spice Route Legal — I'll send the email template when you're ready
  - Questions to bring (I'll prep a doc): age gate sufficiency, system prompt safety language, DPDP deletion obligations, Section 67/67A exposure for Phase 2 content
  - **Deadline:** before paywall flip-on (week 4-5)

- [ ] **Privacy Policy + Terms of Service draft review** _(30 min)_
  - I'll draft them in week 1 using Termly + custom additions; you read them and approve before they go live
  - **Deadline:** before bot launch in week 1

### P3 — content / growth

- [ ] **Decide if your face/voice ever appears in Nila content** _(thinking only)_
  - The AI Nila is the on-screen character. But: if you're willing to be the *voice* of Nila for one or two videos (Tamil voiceover), that's a viral hook. Or fully no — AI voice for everything.
  - Either is fine. Just decide before week 4 when content production starts.
  - **Deadline:** week 3

- [ ] **Send me 5–10 reference photos of "girls who look like Nila"** _(15 min)_
  - For training Nila's character LoRA. Doesn't need to be one specific person — could be a vibe board (Tamil college girls, ~22, casual home photos).
  - These are *reference for AI generation*, not used directly. Avoid celebrities.
  - **Deadline:** week 2

---

## Decided / locked

| # | Decision | Locked value | Date |
|---|---|---|---|
| 1 | Spice ceiling | Phase 2 (sensual, not explicit) + age gate + track explicit-demand signal for future Nila+ tier | 2026-04-29 |
| 2 | 90-day capital | ₹70-75K cash budget; no Meta ads; no meme seeding; AI video IG account = growth engine; lawyer call deferred to week 4-5 | 2026-04-29 |
| 3 | Founder time commitment | "Whatever it takes" — assume 15-20 hrs/week on content, customer conversations, IG engagement, decision review | 2026-04-29 |
| 4 | Brand identity & legal entity | Nila is the brand, no founder face. Sole Proprietorship registered as **"Nila Labs"** via Udyam. Razorpay trade name "Nila Labs" → checkout displays "Nila" → user-facing anonymity preserved. Pvt Ltd deferred to month 5+. | 2026-04-29 |
| 5 | Ethical red lines | Agreed: (1) no minors / age regression / minor-coded scenarios; (2) no named real-person impersonation, archetype roleplay only; (3) no self-harm play-through, break character → iCall 9152987821 + Vandrevala 1860-2662-345; (4) no deception when fourth wall broken seriously — confirm AI when sincerely asked. | 2026-04-29 |

---

## How this file works

- **Add** — agent adds items here when blocked on Naveen-only action
- **Tick** — Naveen marks `[x]` when done, or replies in chat and agent updates
- **Archive** — when an item is done and no longer relevant, move it under "Decided / locked" or delete
- **Priorities:** P0 = blocks next phase, P1 = blocks week 2, P2 = blocks week 4-5, P3 = nice to have / async
