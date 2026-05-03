# Ops runbook

Practical commands for deploying, debugging, and recovering the Nila stack.

---

## Prerequisites (one-time)

- AWS CLI v2, Docker Desktop, PowerShell.
- `aws configure` with an IAM user (root only as fallback — see `founder-actions.md` P3).
- `.env` files at `D:\nila\.env` and/or `D:\nila\backend\.env` containing at minimum:
  - `GEMINI_API_KEY`
  - `SECRET_KEY`
  - `DATABASE_URL` (Supabase pooler — see `supabase-pooler-migration.md`)
  - `TELEGRAM_BOT_TOKEN`
  - `BACKEND_BASE_URL` (HTTPS URL of the ECS service)
  - `CORS_ORIGINS` (comma-separated; include the Vercel domain)

---

## Deploy backend (build → push → roll out)

```powershell
Set-Location d:\nila\backend\aws
.\deploy.ps1
```

What it does:
1. `aws cloudformation deploy` → `nila-aws-base` (ECR + IAM).
2. `docker build` in `d:\nila\backend`, tag to ECR URI, `docker push` (`:latest`).
3. `aws cloudformation deploy` → `nila-aws-app` with parameters from env.
4. `aws ecs update-service --cluster default --service nila-api --region us-east-1 --force-new-deployment` — required because CFN often reports "no changes" when only the digest changed.

Last known good API base: `https://ni-eaaf5ac517554c0680283ea0e67f2525.ecs.us-east-1.on.aws`.

---

## Deploy frontend

The frontend is a Vercel project. Either:
- Push to the connected git branch (Vercel auto-deploys), or
- `vercel --prod` from `frontend/` if linked locally.

If the ECS endpoint changes, update **`frontend/vercel.json`** rewrite target before deploy.

---

## Database migrations

There is no Alembic. The schema log is **`backend/sql/supabase_align_schema.sql`**.

When models add columns:
1. Add `ALTER TABLE ... ADD COLUMN IF NOT EXISTS ...` to that file.
2. Run it in **Supabase Dashboard → SQL Editor** before deploying the new image.
3. Commit the SQL change.

Already-included columns: `users.{display_name,age_confirmed,vibe,telegram_id,subscription_tier}`, `telegram_sessions.*` (incl. `pending_age_text`).

---

## Verifying a deploy

1. `GET /` → 200. (Process is up; doesn't prove DB.)
2. `POST /token` with intentionally wrong creds → **401** (not 500). Confirms DB reachable.
3. Send a Telegram message to `@meetnila_bot` → expect a reply.
4. Send a chat from the web frontend → expect bubbles.

---

## CloudWatch — what to grep

In **CloudWatch Logs** for the ECS task log group:

| Symptom | Look for |
|---------|----------|
| DB unreachable | `psycopg2.OperationalError`, `Network is unreachable`, `Operational connection` |
| Pooler URL wrong | `password authentication failed`, `Tenant or user not found` |
| Schema drift | `UndefinedColumn`, `column ... does not exist`, `pending_age_text` |
| Gemini issues | `google.api_core.exceptions`, `RESOURCE_EXHAUSTED`, `INVALID_ARGUMENT`, `400` |
| Telegram | `Telegram sendMessage HTTP`, `setWebhook` |
| App startup OK | `database engine: host=...`, `Webhook set to ...` |

---

## Rollback (fast)

If a new image breaks:

```powershell
# Find a previous image digest from ECR
aws ecr list-images --repository-name nila-backend --region us-east-1 `
  --query "imageIds[].imageDigest" --output table

# Tag a known-good digest as :latest (replace <digest>)
$digest = "<sha256:...>"
aws ecr batch-get-image --repository-name nila-backend --region us-east-1 `
  --image-ids imageDigest=$digest --query "images[].imageManifest" --output text > manifest.json
aws ecr put-image --repository-name nila-backend --region us-east-1 `
  --image-tag latest --image-manifest file://manifest.json

# Force the service to roll
aws ecs update-service --cluster default --service nila-api --region us-east-1 --force-new-deployment
```

(For zero-downtime rollback later, switch to immutable image tags + CFN parameter swap.)

---

## Common gotchas

- **`#` in `DATABASE_URL` password** must be `%23`. Same for `@ : / ? %` and space. URL parsers silently truncate at the unencoded char. See `supabase-pooler-migration.md`.
- **Region mismatch** — DB in `ap-southeast-2`, app in `us-east-1` (~200ms RTT). Tracked in `founder-actions.md` P3.
- **Stale tasks** — if you skip `force-new-deployment`, ECS keeps old `:latest`. Always run the deploy script (it does this) or call it manually.
- **Vercel CDN caching** — `frontend/vercel.json` already sets `x-vercel-enable-rewrite-caching: 0` on `/api`; do not remove without thinking.
- **CORS** — `CORS_ORIGINS` is read at deploy time into the CFN param; updating only AWS Console env without redeploying CFN will drift from local `.env`.
- **Telegram webhook** — set on app startup if `BACKEND_BASE_URL` is provided; manually re-trigger by restarting tasks if needed.

---

## Smoke test checklist (post-deploy)

- [ ] `GET /` → 200
- [ ] `POST /token` (bad creds) → 401
- [ ] `POST /register` (fresh username) → 200 + token
- [ ] Web `/chat` returns bubbles
- [ ] Telegram `/start` → onboarding messages
- [ ] CloudWatch shows no `OperationalError` in last 5 min
