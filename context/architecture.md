# Architecture overview (one-pager)

*Last updated: 2026-05-01.*

## System map

```
+--------------------+        +---------------------+         +-------------------------+
|  Telegram client   | ---->  | Telegram BotFather  | ---->   |  ECS Express (Fargate)  |
|  (user)            |        |  webhook delivery   |         |  Region: us-east-1      |
+--------------------+        +---------------------+         |  Service: nila-api      |
                                                              |  FastAPI (Uvicorn:8080) |
+--------------------+        +---------------------+         |                         |
|  Web browser       | -----> | Vercel (frontend)   | ----->  |  /api/* origin          |
|  (user)            |        | nila-ashy.vercel... |         |                         |
+--------------------+        +---------------------+         +-----------+-------------+
                                                                          |
                                                              +-----------v-------------+
                                                              |  Supabase Postgres      |
                                                              |  Supavisor pooler       |
                                                              |  ap-southeast-2:6543    |
                                                              +-------------------------+
                                                                          ^
                                                                          |  HTTPS
                                                              +-----------+-------------+
                                                              |  Google Generative AI   |
                                                              |  gemini-3-flash-preview |
                                                              +-------------------------+
```

## Distribution (launch)

**Public funnel:** Instagram (and LinkedIn if used) → **Telegram only** — single CTA `https://t.me/<bot>`. No marketing landing page or custom domain in the primary path until post-traction (see `founder-actions.md` P0, `product-state.md`, `DECISIONS.md`). The Vercel web app is a **secondary** surface (friends, testing, future pivot), not the IG acquisition CTA.

## Components

| Layer | Tech | Path |
|-------|------|------|
| Frontend | React + Vite + Tailwind, hosted on Vercel | `frontend/` |
| API | FastAPI + Uvicorn, port 8080, Docker | `backend/main.py`, `backend/Dockerfile` |
| Telegram | Webhook handler in same FastAPI process | `backend/telegram_bot.py` |
| Brain | Gemini `gemini-3-flash-preview` via `google-genai` | called from `main.py` and `telegram_bot.py` |
| Safety | Pre-LLM classifier for hard refusals | `backend/safety.py` |
| Prompt | Composable system instruction blocks | `backend/prompts.py` |
| Time | IST helpers (display, "today" windows) | `backend/nila_time.py` |
| DB | Supabase Postgres via Supavisor pooler (psycopg2 + SQLAlchemy) | `backend/database.py`, `backend/models.py` |
| Schema | Idempotent `ALTER TABLE` script (no Alembic) | `backend/sql/supabase_align_schema.sql` |
| Auth | OAuth2 password flow, JWT (HS256) | `backend/auth.py` |
| Infra | CloudFormation: ECR + IAM (`nila-aws-base`), ECS Express service (`nila-aws-app`) | `backend/aws/cloudformation/*.yaml`, `backend/aws/deploy.ps1` |

## Data flow

**Web `/chat`**
1. Browser → `https://<vercel>/api/chat` (Bearer JWT).
2. Vercel rewrites `/api/(.*)` → ECS origin.
3. FastAPI: safety check → save user msg → build IST-stamped Gemini history → `client.models.generate_content(...)` → `|`-split bubbles → save model msgs → return.
4. DB writes via SQLAlchemy session → Supabase pooler (transaction mode).

**Telegram message**
1. Telegram → ECS `POST /telegram/webhook`.
2. Lookup/create `TelegramSession` (onboarding state).
3. If onboarding: name → LLM age gate (PASS/FAIL/UNCLEAR with one clarify) → free-text "why" → Gemini-generated opening bubbles.
4. Else: safety → daily IST limit (15 free) → `_generate_nila_reply` (same Gemini path as web) → `_tg_send_bubbles`.

## Schema (current models)

| Table | Notable columns |
|-------|-----------------|
| `users` | `username`, `hashed_password`, `display_name`, `age_confirmed`, `vibe`, `telegram_id` (unique), `subscription_tier` (free/close/closer) |
| `messages` | `content`, `role` (user/model), `timestamp` (naive UTC), `user_id` |
| `telegram_sessions` | `telegram_id` (unique), `onboarding_step` (none/await_name/await_dob/await_dob_clarify/await_vibe/blocked_age/done), `display_name`, `age_confirmed`, `vibe`, `pending_age_text`, `created_at`, `updated_at` |

## Environment variables (ECS task)

| Name | Purpose |
|------|---------|
| `DATABASE_URL` | Supabase pooler URI (sslmode=require, password percent-encoded) |
| `GEMINI_API_KEY` | Google Generative AI |
| `SECRET_KEY` | JWT signing |
| `CORS_ORIGINS` | Comma-separated origins |
| `TELEGRAM_BOT_TOKEN` | BotFather token |
| `BACKEND_BASE_URL` | Used to register Telegram webhook on startup |
| `PORT` | 8080 |
| (legacy, unused after pooler) | `DATABASE_PREFER_IPV4`, `DATABASE_HOSTADDR`, `DATABASE_IPV4_DNS_FALLBACK` |

## External dependencies

- **Supabase** — Postgres + pooler.
- **AWS** — ECR + ECS Express + IAM.
- **Vercel** — frontend + `/api/*` rewrite.
- **Google Generative AI** — Gemini.
- **Telegram BotFather** — `@meetnila_bot`.
- **Razorpay** (future) — payments.

## Cross-cutting notes

- **Health check** (`GET /`) does **not** touch the DB; do not mistake 200 there for full system health. Use `POST /token` with bad creds to confirm DB reachability (expect 401, not 500).
- **IST everywhere user-visible.** UTC stays in the DB.
- **No Alembic.** Treat `supabase_align_schema.sql` as the migration log; append `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` whenever models gain columns.
