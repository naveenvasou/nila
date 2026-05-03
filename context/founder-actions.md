# Founder action items — Naveen

Tracker for things only Naveen can do (decisions, signups, KYC, name reservations, etc.). The CEO/agent maintains this file; tick items off as they're done. Items added here only when execution is blocked on a real-world action.

Last updated: 2026-05-01 (payments + domain/website deferred; IG → Telegram single funnel)

---

## Infrastructure notes (for future you)

**Supabase + AWS Fargate / ECS — IPv6 “network unreachable” (RESOLVED 2026-04-30).** Supabase removed IPv4 from the direct `db.<project>.supabase.co` host (AAAA-only); ECS Express / Fargate has no IPv6 egress, so Postgres failed with `Network is unreachable` while `GET /` returned 200.

- **Fix in place:** `DATABASE_URL` switched to the **Supabase Supavisor pooler** — host `aws-1-ap-southeast-2.pooler.supabase.com:6543` (transaction mode), username `postgres.<project-ref>`, `sslmode=require`. The pooler has real IPv4 records; no `hostaddr` hack needed.
- **Password gotcha:** the DB password contains `#` — **must be percent-encoded as `%23`** in `DATABASE_URL`. Same for any other URL-reserved chars (`@ : / ? %` space) if rotated.
- **Dead code:** the IPv4-pinning logic in `backend/database.py` (`_postgres_ipv4_hostaddr`, Google-DNS fallback, `hostaddr` injection, `DATABASE_PREFER_IPV4` / `DATABASE_HOSTADDR` / `DATABASE_IPV4_DNS_FALLBACK` envs) is no longer needed. See P3 cleanup task below.
- **Operational:** After changing DB connectivity, redeploy the API image (`backend/aws/deploy.ps1`) and confirm CloudWatch shows no `OperationalError` on `/register` or `/telegram/webhook`.

---

## Pending

### P0 — ship the funnel (IG → Telegram only)

**Principle:** one public pathway — bios and posts point **only** to the Telegram bot (`t.me/...`). No marketing website, no custom domain, and no “also try our web app” in the main funnel until we have traction and deliberately add a second surface. If Telegram proves wrong, we may pivot (web app, etc.); until then, optimize the Telegram experience.

- [ ] **Pick + create the Instagram account** _(15 min, ~₹0)_
  - Check availability: `@hellonila`, `@nila.chennai`, `@nila.tanglish` — reply with which return "user not found"
  - Create the chosen handle (can stay private until content is ready)
  - **Bio + pinned story:** single CTA → **`https://t.me/meetnila_bot`** (or final bot handle). LinkedIn bio same rule if you use it.
  - **Why:** IG is the distribution engine; Telegram is the product. No split attention for strangers.
  - **Deadline:** before first public IG push

- [x] ~~**Telegram bot handle reserved** — `@meetnila_bot`~~ _(already done)_

- [x] ~~**Confirm decision #5 — ethical red lines** — agreed 2026-04-29~~

- [x] ~~**Review revised system prompt (prompts.py)** — approved 2026-04-30~~

### P1 — needed before public launch

- [ ] **Privacy Policy + Terms of Service draft review** _(30 min)_
  - I'll draft them in week 1 using Termly + custom additions; you read them and approve before they go live
  - **Host links:** acceptable v1 surfaces include Termly/Notion/public doc + link from **Telegram bot description** and/or pinned message — **no custom domain required** until post-traction.
  - **Why:** public launch should not collect user data / run companion chat without basic terms and privacy language.
  - **Deadline:** before public bot launch

### Post-traction — brand + web surface (after IG / Telegram validation)

**Do not block shipping on this.** Revisit once you have real users and signal that Nila is sticking (or once squatting risk outweighs cost).

- [ ] **Buy domains as brand insurance** _(15 min, ~₹1–2K)_ — `nila.app`, `nila.in` (or chosen TLDs)
  - **Why later, not now:** product is Telegram-first; domains do not make the bot work. Buy when you want a stable link for email, redirects, or a future landing page — not a prerequisite for “people try Nila on Telegram.”
  - **Deadline:** after first meaningful traction OR before a wider PR push (whichever comes first)

- [ ] **Optional: one-page site or owned-domain redirect** _(later)_
  - Only if you add a second pathway on purpose (e.g. `nila.app` → 301 to `t.me/...`, or host Privacy/ToS on your own domain). Until then, policy links can live in bot description / pinned message / simple third-party host (see P1 Privacy/ToS).

### Post-launch monetization prep — do not start until launch validation

We explicitly decided on 2026-05-01 to **launch first, learn, then monetize**. These tasks remain here so they are not forgotten, but they are **not today's work** and should not block public launch unless strategy changes.

- [ ] **Udyam (MSME) registration as "Nila Labs"** _(10 min, free)_
  - Go to [udyamregistration.gov.in](https://udyamregistration.gov.in/)
  - Enter Aadhaar + PAN, business name "Nila Labs", classify as "Services — IT/Software"
  - Save the Udyam certificate PDF
  - **Why:** required for Razorpay to display "Nila" on checkout instead of your personal name.
  - **Deadline:** post-launch, before enabling paid plans

- [ ] **Open / designate a current account in "Naveen Kumar Ezhumalai trading as Nila Labs"** _(2-3 days, ~₹0)_
  - ICICI / HDFC / Kotak all do this for sole props
  - Bring: Aadhaar, PAN, Udyam certificate, address proof
  - Or: convert your existing savings account if your bank allows
  - **Why:** Razorpay payouts land here. Bank statement entries on user side will show "Nila" merchant descriptor.
  - **Deadline:** post-launch, before enabling paid plans

- [ ] **Razorpay account onboarding** _(1 day, free)_
  - Create Razorpay account, do business KYC with Udyam + bank account + PAN
  - Set business display name to **"Nila"**, merchant descriptor to **"NILACHAT"**
  - **Why:** payments rail.
  - **Deadline:** post-launch, before enabling paid plans

### P2 — needed before monetization / higher-risk growth

- [ ] **1-hour call with Indian tech lawyer** _(1 hr + ₹15-25K)_
  - Shortlist: Ikigai Law, NovoJuris, Spice Route Legal — I'll send the email template when you're ready
  - Questions to bring (I'll prep a doc): age gate sufficiency, system prompt safety language, DPDP deletion obligations, Section 67/67A exposure for Phase 2 content
  - **Deadline:** before paywall flip-on or higher-risk Phase 2 content

### P3 — operational hygiene

- [ ] **Migrate ECS service from `us-east-1` to `ap-southeast-2`** _(30-60 min)_
  - DB now lives in Sydney (Supabase pooler `aws-1-ap-southeast-2.pooler.supabase.com`); ECS still in N. Virginia. Every query crosses the Pacific (~200ms RTT).
  - Re-deploy CloudFormation stacks (`nila-aws-base`, `nila-aws-app`) with `$env:AWS_REGION = "ap-southeast-2"` before running `backend/aws/deploy.ps1`. Update `frontend/vercel.json` rewrite to the new ECS endpoint after deploy.
  - **Why:** noticeably faster auth + chat endpoints; cheaper cross-AZ traffic; users in India/SEA closer to Sydney than Virginia.
  - **Deadline:** anytime; not blocking, but every week of delay = slow UX.

- [ ] **Remove dead IPv4-pinning code from `backend/database.py`** _(15 min)_
  - With Supabase pooler in use, `_postgres_ipv4_hostaddr`, `_ipv4_via_google_public_dns`, `_inject_ipv4_hostaddr_into_url`, the `hostaddr` `connect_args`, and the `DATABASE_PREFER_IPV4` / `DATABASE_HOSTADDR` / `DATABASE_IPV4_DNS_FALLBACK` envs are unused. Keep only URL normalization + `sslmode=require`.
  - **Why:** removes ~80 lines of complexity + a Google-DNS HTTPS dependency on every cold start.
  - **Deadline:** anytime; safe whenever the pooler URL is the only DB path.

- [ ] **Pick a URL-safe DB password on next Supabase rotation** _(2 min)_
  - Avoid `# @ : / ? %` and space — they need percent-encoding in `DATABASE_URL` and break various env-file / shell parsers silently. Stick to `A-Z a-z 0-9 - _ . ~`.
  - **Why:** the `#` in the current password already cost us debugging time once.

- [ ] **Stop using AWS root account for daily ops** _(15 min)_
  - Create an IAM admin user (yourself), enable MFA, save credentials
  - Run `aws configure` again with the new keys
  - Lock down root: enable MFA on root + remove its access keys
  - **Why:** root has unconditional access to everything including billing/credit management. If your laptop ever gets compromised, you lose the AWS account. Industry-standard hygiene.
  - **Deadline:** within 30 days, but easy enough to do anytime

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
| 6 | Payments timing | Launch free first; defer Udyam/current account/Razorpay/paywall work until post-launch validation. | 2026-05-01 |
| 7 | Distribution funnel | **IG (and LinkedIn if used) → Telegram only** for public launch. No custom domain or marketing website in the primary funnel until post-traction; avoids two pathways. Domains = optional **brand insurance** after validation. If Telegram underperforms, pivot channel/product shape is allowed. | 2026-05-01 |

---

## How this file works

- **Add** — agent adds items here when blocked on Naveen-only action
- **Tick** — Naveen marks `[x]` when done, or replies in chat and agent updates
- **Archive** — when an item is done and no longer relevant, move it under "Decided / locked" or delete
- **Priorities:** P0 = blocks immediate launch path, P1 = needed before public launch, P2 = needed before monetization / higher-risk growth, P3 = nice to have / async
