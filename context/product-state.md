# Product state (living)

*Update this file when phase or priorities shift. Keep it short — link out for depth.*

Last updated: **2026-05-01**

## One-liner

Nila — Tanglish-native AI companion for India. **Launch surface: Instagram (and LinkedIn if used) → Telegram only** — one CTA (`t.me/...`); no marketing site or custom domain in the public funnel until traction justifies it. Web app exists for dev / friends / future pivot, not the IG acquisition path. Free first; payments deferred until post-launch validation.

## Current phase

**Pre-launch / week 1.** Backend + Telegram path is live and DB-stable on Supabase pooler. **Distribution plan:** ship a great Telegram experience, go live on IG with a **single link** to the bot, learn whether people stay — then decide on domains, landing pages, or web/mobile pivot. **Do not build payments or a second acquisition funnel before that.**

## Shipped

**Backend (FastAPI on AWS ECS Express, ECR `nila-backend`)**
- Routes: `POST /register`, `POST /token`, `GET /history`, `POST /chat`, `POST /telegram/webhook`, `GET /` health.
- **Gemini** (`gemini-3-flash-preview`) generation; `|`-split bubbles for multi-message replies.
- **Safety classifier** (`backend/safety.py`) runs **before** Gemini for hard refusals.
- **System prompt** in `backend/prompts.py` (character, texting style, romantic arc, hard refusals).

**Telegram bot (`backend/telegram_bot.py`)**
- Single-service: same FastAPI process handles webhook.
- Onboarding: name → **free-text age, classified by Gemini** (PASS/FAIL/UNCLEAR; one clarify; fail-closed) → free-text "why are you here?".
- First in-character burst is **LLM-generated** (with a short fallback) — no fixed script.
- Daily free-tier limit: **15 user messages / IST calendar day**.
- Webhook auto-registered on app startup if `BACKEND_BASE_URL` is set.

**Time / locale**
- `backend/nila_time.py`: DB stores **naive UTC**; display + "today" windows use **Asia/Kolkata (IST)** for `/history`, `/chat` Gemini context, Telegram counters.
- Frontend (`frontend/src/Chat.tsx`) optimistic bubble times also formatted in IST.

**DB / connectivity**
- **Supabase Postgres via Supavisor pooler** (transaction mode, port 6543) — see `supabase-pooler-migration.md`.
- Schema alignment script: `backend/sql/supabase_align_schema.sql` (idempotent `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`).
- Models: `User`, `Message`, `TelegramSession` (incl. `pending_age_text` for age clarify).

**Frontend (Vercel + React + Vite)**
- `frontend/vercel.json` rewrites `/api/(.*)` → ECS origin; `x-vercel-enable-rewrite-caching: 0` on `/api`.
- Dev: Vite proxy `/api → http://127.0.0.1:8080`.

**Infra / deploy**
- `backend/aws/deploy.ps1` — build → ECR push → CFN (`nila-aws-base`, `nila-aws-app`) → forced ECS rollout.

## Next (engineering)

**P0 — operational hygiene**
- Run `backend/sql/supabase_align_schema.sql` whenever a model adds columns (e.g. `telegram_sessions.pending_age_text` already added).
- Smoke-test: `/register`, `/token`, `/chat`, `/telegram/webhook` after every deploy.

**P1 — launch readiness**
- Web onboarding parity (web users currently start with `age_confirmed=False`; comment in `main.py` flags this for week 2).
- Telegram/web smoke testing with a small real-user circle.
- Tighten first-run copy, failure messages, and safety edge cases from test chats.
- Keep the free daily limit; payment integration is explicitly **post-launch**, not this phase.

**P2 — performance / region**
- **Migrate ECS to `ap-southeast-2`** (DB lives there; current US ↔ AU adds ~200ms RTT). See `founder-actions.md` P3.
- **Remove dead IPv4-pinning code** in `backend/database.py` (Google DNS fallback, `hostaddr` injection, `DATABASE_PREFER_IPV4`/`DATABASE_HOSTADDR`/`DATABASE_IPV4_DNS_FALLBACK` envs). Pooler eliminates the need.

**P3 — product polish**
- Long-term memory / fact extraction (models scaffolded; not wired into prompt yet).
- Rate-limit copy that frames the daily cap without requiring a live payment link.
- Real-time typing pacing tuning.

## Next (founder)

See **`founder-actions.md`** in this folder. Highlights:
- **P0** — IG account + bio/pin: **only** `t.me` bot link; no website/domain in the funnel yet.
- **P1** — Privacy Policy / ToS (link can live in bot description / Termly / Notion — **no owned domain required** for v1).
- **Post-traction** — buy domains as brand insurance; optional site or redirect when we add a second surface on purpose.
- **Post-launch** — Udyam, current account, Razorpay, lawyer before monetization.

## Non-goals (for now)

- Voice / video Nila (post first paid cohort).
- Custom **marketing website** or **second primary user pathway** (e.g. “try web and Telegram”) in the **IG funnel** before Telegram+IG validation.
- Buying **domains** as a launch prerequisite (optional **brand insurance** after traction — see `founder-actions.md`).
- Open web signup with no age gate.
- Multi-language beyond Tanglish/Tamil/English (Hindi etc. deferred).
- Self-hosted DB / multi-region active-active.
- Native mobile apps (Telegram + responsive web is enough for v1).

## Pointers

- Architecture overview: `architecture.md`
- Deploy / rollback / debug: `ops.md`
- DB connectivity rationale: `supabase-pooler-migration.md`
- Strategy long-form: `claude_CEO_conversation.md` and `canvases/nila-go-to-market.canvas.tsx`
