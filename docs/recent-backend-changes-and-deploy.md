# Recent backend changes & deploy commands (debug aid)

This file summarizes what changed across the **last few rounds of work** in this repo (IST / Telegram UX, LLM age gate, schema), and the **exact commands used to redeploy**. Use it when the backend “stopped working” to diff expectations vs. production (DB columns, env, image rollout).

---

## 1. India Standard Time (IST)

**Goal:** UI and model context showed times **5h 30m behind** users in IST because DB timestamps are **naive UTC** and were formatted as local UTC wall clock.

| File | Change |
|------|--------|
| `backend/nila_time.py` | **New.** `ZoneInfo("Asia/Kolkata")` helpers: `utc_naive_to_ist`, `format_time_ampm_ist`, `format_timestamp_gemini_ist`, `ist_today_date`, `ist_day_start_utc_naive` / `ist_day_end_utc_naive` for “today” windows. |
| `backend/main.py` | Import `format_time_ampm_ist`, `format_timestamp_gemini_ist`. **`GET /history`:** message `time` uses IST. **`POST /chat`:** Gemini history bracket timestamps use IST. |
| `backend/telegram_bot.py` | Import nila_time helpers. **`_messages_today`:** counts user messages in the **IST calendar day** (not UTC midnight). **`_generate_nila_reply`:** history lines use IST timestamps. |
| `frontend/src/Chat.tsx` | **`formatNowIST()`** — `toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', ... })` for optimistic user/Nila bubble times so they match `/history`. |
| `backend/prompts.py` | `ConversationContext.vibe` docstring updated (free-text “why here”). |

---

## 2. Telegram onboarding (less rigid script)

**Goal:** Remove fixed **1 / 2 / 3** “vibe” menu and rigid closing line; keep compliance-ish steps but softer copy.

| File | Change |
|------|--------|
| `backend/telegram_bot.py` | **`OnboardingStep`:** `AWAIT_VIBE` still stored as `await_vibe` but collects **free text** (“what are you mostly here for?”). **`_gemini_telegram_opening`:** after onboarding, first in-character burst from **Gemini** (`gemini-3-flash-preview`), `|`-split bubbles; **`_opening_fallback_bubbles`** on failure. Central **`TG_*`** strings for copy. Removed **`VIBE_OPTIONS`** dict. |

---

## 3. Telegram age: free text + LLM (no DOB parsing)

**Goal:** Drop **YYYY-MM-DD** regex UX; classify age with **Gemini**.

| File | Change |
|------|--------|
| `backend/telegram_bot.py` | **`_llm_classify_age_gate`**, **`_normalize_age_verdict`**. Steps: **`await_dob`** (free text) → **`await_dob_clarify`** if UNCLEAR (stores first reply in **`pending_age_text`**) → **`blocked_age`** on FAIL / fail-closed unclear. **`BLOCKED_AGE`:** non-`/start` messages get **`TG_BLOCKED_HINT`**. **`/start`:** clears **`pending_age_text`**. Removed **`import re`** and all regex DOB parsing. |
| `backend/models.py` | **`TelegramSession.pending_age_text`** — `Column(String(2000), nullable=True)`. |
| `backend/sql/supabase_align_schema.sql` | **`pending_age_text`** on `telegram_sessions` in **CREATE TABLE** + **`ALTER TABLE ... ADD COLUMN IF NOT EXISTS`**. |

**Critical for production:** If Supabase was **never** updated after this change, any code path that **reads/writes `telegram_sessions.pending_age_text`** can cause **500s / DB errors** until you run the align SQL (at least line 29) in the Supabase SQL editor.

---

## 4. Deploy commands used (PowerShell, Windows)

From repo machine, with **`GEMINI_API_KEY`** and **`SECRET_KEY`** set (or loaded from **`D:\nila\.env`** / **`D:\nila\backend\.env`** per script rules):

```powershell
Set-Location d:\nila\backend\aws
.\deploy.ps1
```

What the script does (summary):

1. `aws cloudformation deploy` — **`nila-aws-base`** (ECR + IAM).
2. Docker **build** in **`d:\nila\backend`**, **tag** to ECR URI, **`docker push`**.
3. `aws cloudformation deploy` — **`nila-aws-app`** (parameters from env, including **`DATABASE_URL`**).
4. Deletes temp param JSON.
5. **`aws ecs update-service --cluster default --service nila-api --region us-east-1 --force-new-deployment`** (so **`:latest`** digest changes actually roll tasks).

**Last successful run (from session logs):** account **238337501442**, region **`us-east-1`**, API base **`https://ni-eaaf5ac517554c0680283ea0e67f2525.ecs.us-east-1.on.aws`**, image digest **`sha256:105bcf50a75c9d08cc6959a00ee304e6a07ebe165abc423d9d5c5df3332e2e6a`**, script **exit code 0**.

Optional checks:

```powershell
aws sts get-caller-identity
aws ecs describe-services --cluster default --services nila-api --region us-east-1 --query "services[0].deployments"
```

---

## 5. If “backend not working” — quick checklist

1. **`GET /`** on the ECS URL — if **200**, process is up; failures are often **DB / Telegram / Gemini** on specific routes.
2. **CloudWatch** — traceback on **`/register`**, **`/telegram/webhook`**, **`/chat`**: **`OperationalError`** → Postgres / **`DATABASE_URL`**; **`UndefinedColumn`** / **`pending_age_text`** → run **`supabase_align_schema.sql`** (or equivalent migration).
3. **Supabase** — confirm **`telegram_sessions.pending_age_text`** exists after the Telegram age changes.
4. **Stale tasks** — confirm new deployment is **PRIMARY** and tasks pulled the new digest after **`force-new-deployment`**.

---

## 6. Related doc (DB connectivity)

Current approach: **`context/supabase-pooler-migration.md`** (Supabase pooler + `DATABASE_URL` on ECS).

---

*Generated to support debugging “what changed + how we deployed.”*
