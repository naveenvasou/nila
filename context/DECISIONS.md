# Decision log (living)

Format per entry: **YYYY-MM-DD — Decision — Rationale** (and *Alternatives*).

Strategy / business decisions also appear in `founder-actions.md` ("Decided / locked"); engineering-flavored decisions are captured here so future agents understand *why the code looks the way it does*.

---

## Strategy / business

- **2026-05-01 — Public acquisition funnel = IG (and LinkedIn if used) → Telegram only.** Single CTA (`t.me/...`); no custom domain, no marketing landing page, and no “second pathway” in the main funnel until we have traction and choose to add one. Domains (`nila.app` / `nila.in`) are **post-traction brand insurance**, not a launch prerequisite. If Telegram underperforms, pivoting to web or mobile is allowed — we are not over-investing in web surface before channel validation. *Alt: buy domains early → cheap insurance but not required for Telegram-only learning.*
- **2026-05-01 — Payments / Razorpay deferred until after launch validation.** Launch should prove retention, tone, safety, distribution, and basic ops before founder time goes into Udyam/bank/Razorpay integration. Keep `subscription_tier` and daily caps as scaffolding, but do not build paywall flows until post-launch signal is clear. *Alt: build payments before launch → slows learning and adds compliance/setup drag before demand is proven.*
- **2026-04-29 — Spice ceiling = Phase 2 (sensual, not explicit) + age gate; track explicit-demand for future Nila+ tier.** Keeps app payment-rail-friendly while leaving headroom. *Alt: explicit by default → blocked Razorpay/UPI risk; or Phase 1 only → leaves money on the table.*
- **2026-04-29 — 90-day capital plan: ₹70–75K cash, no Meta ads, no meme seeding; AI-video Instagram is the growth engine.** Optimizes for Tamil cultural fit and CAC near zero; lawyer call deferred to week 4–5.
- **2026-04-29 — Founder commits 15–20 hrs/week** ("whatever it takes") to content, customer conversations, IG engagement, decision review.
- **2026-04-29 — Brand = "Nila"; legal entity = Sole Proprietorship "Nila Labs" (Udyam).** Razorpay trade name "Nila Labs" → checkout displays "Nila"; founder face never appears. Pvt Ltd deferred to month 5+.
- **2026-04-29 — Ethical red lines locked:** no minors / age regression / minor-coded scenarios; no named real-person impersonation (archetypes only); no roleplay through self-harm — break character → iCall 9152987821 + Vandrevala 1860-2662-345; no deception when fourth wall is broken sincerely.

## Engineering / infra

- **2026-04-30 — DB connectivity via Supabase Supavisor pooler, not direct `db.<ref>.supabase.co`.** Supabase removed IPv4 from the direct host; ECS Fargate has no IPv6 egress. Pooler publishes IPv4, no `hostaddr` hack needed. *Alt: enable IPv6 on VPC end-to-end (more infra work); pay Supabase for IPv4 add-on.* See `supabase-pooler-migration.md`.
- **2026-04-30 — Keep ECS in `us-east-1` for now even though DB is in `ap-southeast-2`.** Migration is a single-region redeploy and it's cheap to defer; logged in `founder-actions.md` P3.
- **2026-04-30 — IPv4-pinning code (Google-DNS fallback, `hostaddr`, `DATABASE_PREFER_IPV4`/`DATABASE_HOSTADDR`/`DATABASE_IPV4_DNS_FALLBACK`) is dead but **not yet removed.** Will delete after a week of stable pooler operation. Tracked in `founder-actions.md` P3.
- **2026-04-30 — Telegram age gate switched from regex DOB (`YYYY-MM-DD`) to **free-text + Gemini classifier** (PASS / FAIL / UNCLEAR; one clarify step; fail-closed).** Better UX, no rigid format. *Trade-off:* model can misclassify; mitigated by clarify step + (later) payment KYC. Stored in `telegram_sessions.pending_age_text` between attempts.
- **2026-04-30 — Telegram onboarding "vibe" step changed from 1/2/3 menu to **free-text "what brings you here?"**, and the first in-character message is **LLM-generated** with a short fallback.** Removes hardcoded scripted feel; matches Nila's voice elsewhere.
- **2026-04-30 — Display + "today" windows in IST (Asia/Kolkata).** DB stays naive UTC. Single helper module: `backend/nila_time.py`. *Alt: store tz-aware UTC in DB → larger migration; deferred.*
- **2026-04-30 — `DATABASE_URL` is the only DB config knob.** Schema migrations are an **idempotent SQL file** (`backend/sql/supabase_align_schema.sql`), not Alembic. *Alt: Alembic / Supabase migrations runner — overkill for current scope.*
- **2026-04-30 — Single-service Telegram + web** (one FastAPI process handles webhook), not a worker fleet. *Alt: separate worker service for Telegram → premature; current scale doesn't need it.*
- **2026-04-30 — Force ECS rollout after every image push** (`aws ecs update-service ... --force-new-deployment`). CFN reports "no changes" when only `:latest` digest changed.
- **2026-04-30 — `context/` folder is canonical durable memory** (this file, `product-state.md`, `founder-actions.md` mirror, `claude_CEO_conversation.md`, `supabase-pooler-migration.md`, etc.). `docs/` may diverge over time; agents should prefer `context/` unless explicitly told otherwise.

## Conventions

- **Secrets:** never committed; loaded from `.env` (root + `backend/`) or process env. Deploy script merges them into CFN parameters at deploy time.
- **Schema:** add columns via SQLAlchemy model + a matching `ADD COLUMN IF NOT EXISTS` in `backend/sql/supabase_align_schema.sql`. Run on Supabase before redeploying.

---

*Add new entries on top of each section as they happen.*
