# Agent handoff: ECS ↔ Supabase Postgres connectivity

This document is **delegation context** for a specialized coding/infrastructure agent. Goal: stop **`psycopg2` / SQLAlchemy `OperationalError`** when the FastAPI backend running on **AWS ECS Express (Fargate)** connects to **Supabase Postgres**, while **`GET /`** continues to return **200** (health route does not require the DB).

---

## 1. Problem statement

### Symptoms

- CloudWatch / container logs show failures similar to:

  ```text
  sqlalchemy.exc.OperationalError: (psycopg2.OperationalError)
  connection to server at "db.<project>.supabase.co" (<IPv6 address>), port 5432 failed:
  Network is unreachable
  Is the server running on that host and accepting TCP/IP connections?
  ```

- **`GET /`** succeeds (**200**).
- Endpoints that use **`get_db()`** (SQLAlchemy session) fail (**500** or errors under load), including at least:
  - **`POST /register`**, **`POST /token`** (login)
  - **`GET`** routes protected by JWT that touch the DB (e.g. **`/history`**)
  - **`POST /telegram/webhook`** (uses `Depends(get_db)`)

### Interpretation (working hypothesis)

- Supabase’s DB hostname often resolves to **IPv6 (AAAA)** as well as **IPv4 (A)**.
- Many **Fargate / ECS Express** networking paths **do not provide working IPv6 egress**.
- If **libpq / psycopg2** ends up using **IPv6**, TCP connect fails with **`Network is unreachable`** even though Postgres is up.

The team attempted to **force IPv4** by injecting **`hostaddr=<IPv4>`** while keeping the **TLS Server Name Indication (SNI)** hostname as **`db.<project>.supabase.co`** — **after deploy, the issue reportedly persists.**

---

## 2. Repository & runtime stack

| Layer | Technology |
|--------|------------|
| API | **FastAPI** (`backend/main.py`), **Uvicorn** on **`PORT`** (8080 in ECS) |
| ORM | **SQLAlchemy 2.x-style** engine + `sessionmaker` |
| Postgres driver | **psycopg2** (binary build in container via `libpq`) |
| DB | **Supabase Postgres**; connection string via **`DATABASE_URL`** env on the task |
| Container | **`python:3.12-slim`**, `libpq-dev`, `gcc` (`backend/Dockerfile`) |
| SQLite fallback | If **`DATABASE_URL`** is empty or starts with `sqlite`, app uses **`sqlite:///./nila.db`** inside the container (**ephemeral** — not suitable for production multi-instance). |

---

## 3. What the codebase does today (`backend/database.py`)

Loaded **at import time** (module scope):

1. **`DATABASE_URL`** read from environment (unless empty / sqlite).
2. **Normalize** `postgres://` → `postgresql://`.
3. Ensure **`sslmode=require`** in query string if missing (hosted Postgres expects TLS).
4. **IPv4 pinning attempt**
   - If **`DATABASE_PREFER_IPV4`** is truthy (default **`true`**): resolve DB hostname to an IPv4 and append **`hostaddr=<IPv4>`** to the URI query string.
   - Resolution order:
     - **`DATABASE_HOSTADDR`** — if set and valid IPv4, use as-is.
     - **`socket.getaddrinfo(..., AF_INET)`** — VPC/task resolver.
     - If no IPv4 from libc: **`DATABASE_IPV4_DNS_FALLBACK`** (default **`true`**) triggers HTTPS **`https://dns.google/resolve?name=<host>&type=A`** (Google Public DNS JSON API) to obtain **A** records.
   - **`create_engine(..., connect_args={"hostaddr": "<IPv4>"})`** when `hostaddr` appears in the URL query (belt-and-suspenders; comment notes SQLAlchemy may not always forward URI query params to psycopg2).

**Startup log line** (no secrets):

```text
database engine: host=<hostname> hostaddr_set=True|False pool_pre_ping=True|False
```

If public DNS fallback succeeds:

```text
database: IPv4 from public DNS fallback for host=<hostname>
```

**Hypotheses if errors still show IPv6 after deploy**

- **`hostaddr_set=False`** in logs → IPv4 never resolved (blocked egress to `dns.google`, resolver-only AAAA, or bug).
- **`hostaddr_set=True`** but error still mentions IPv6 → **`hostaddr` not honored** by this SQLAlchemy/psycopg2/libpq path, or different code path / stale tasks.
- **Stale ECS tasks** still running an older image digest despite `:latest` tag — mitigate with **`aws ecs update-service … --force-new-deployment`** after push.

---

## 4. Environment variables (backend / ECS task)

| Variable | Role |
|----------|------|
| **`DATABASE_URL`** | Full Postgres URI (Supabase). Passed into ECS via CloudFormation parameter **`DatabaseUrl`** → task env **`DATABASE_URL`**. |
| **`DATABASE_PREFER_IPV4`** | Default **`true`**. Set **`false`** only if intentionally using IPv6-capable networking. |
| **`DATABASE_HOSTADDR`** | Optional literal **IPv4** for libpq `hostaddr` (escape hatch if DNS/fallback fails). |
| **`DATABASE_IPV4_DNS_FALLBACK`** | Default **`true`**. Set **`false`** to disable Google DNS HTTPS fallback. |
| **`GEMINI_API_KEY`**, **`SECRET_KEY`** | Required by deploy script for CFN; not DB-specific. |
| **`CORS_ORIGINS`** | Comma-separated browser origins. |
| **`TELEGRAM_BOT_TOKEN`**, **`BACKEND_BASE_URL`** | Telegram webhook registration on startup. |

**Deploy-time secret injection:** `backend/aws/deploy.ps1` merges **`D:\nila\.env`** then **`D:\nila\backend\.env`** (backend wins); shell env overrides merged values. It builds **`._cfn_param_overrides.json`** then deletes it; **`DatabaseUrl`** comes from process **`DATABASE_URL`** at deploy time — **changing only secrets in AWS Console without redeploying CFN / updating stack parameters** may drift from local `.env`.

---

## 5. AWS backend deployment

### How deploy works

- **Script:** `backend/aws/deploy.ps1`
- **Prerequisites:** AWS CLI v2, Docker, configured credentials (`aws sts get-caller-identity`).
- **Region:** **`AWS_REGION`** or default **`us-east-1`**.

### CloudFormation stacks

| Stack name | Template | Purpose |
|------------|----------|---------|
| **`nila-aws-base`** | `backend/aws/cloudformation/01-base.yaml` | **ECR** repo (**`nila-backend`**), IAM roles for ECS Express |
| **`nila-aws-app`** | `backend/aws/cloudformation/02-ecs-express.yaml` | **ECS Express Mode** service (**`AWS::ECS::ExpressGatewayService`**), ALB, HTTPS |

### ECS Express service (from template)

- **Resource:** `NilaExpressApi` (`AWS::ECS::ExpressGatewayService`)
- **`ServiceName`:** **`nila-api`**
- **CPU / memory:** 256 / 512
- **Container port:** **8080**
- **`HealthCheckPath`:** **`/`**
- **Environment** passed to container includes **`DATABASE_URL`**, **`GEMINI_API_KEY`**, **`SECRET_KEY`**, **`CORS_ORIGINS`**, **`TELEGRAM_BOT_TOKEN`**, **`BACKEND_BASE_URL`**, **`PORT=8080`**

### ECR & image

- **Repository name:** **`nila-backend`**
- **Tag:** **`latest`** (script builds `nila-backend:latest`, tags to full **`EcrImageUri`**, pushes).

### Post-deploy rollout

CloudFormation often reports **“No changes”** when only the **`latest` digest** changes. Script runs:

```powershell
aws ecs update-service --cluster default --service nila-api --region <region> --force-new-deployment
```

If cluster/service names differ in your account, update **`deploy.ps1`** accordingly.

### Known deploy output (example — verify in your account)

- **API endpoint (HTTPS):**  
  **`https://ni-eaaf5ac517554c0680283ea0e67f2525.ecs.us-east-1.on.aws`**
- **AWS account** from a successful local deploy log (confirm with `sts get-caller-identity`): **238337501442**

---

## 6. Frontend deployment & how traffic reaches the API

### Hosting

- **Frontend:** **Vercel** (React + Vite).

### Browser API base URL

- **`frontend/src/config.ts`**: **`API_URL`** defaults to **`"/api"`** (same origin).
- Optional override: **`VITE_API_URL`** (trimmed, trailing slashes stripped).

### Vercel rewrites (production)

**File:** `frontend/vercel.json`

- **`/api/(.*)`** → proxied to the **ECS Express HTTPS origin** (currently configured as):

  **`https://ni-eaaf5ac517554c0680283ea0e67f2525.ecs.us-east-1.on.aws/$1`**

- SPA fallback: **`/(.*)`** → **`/index.html`**

### Headers

- **`/api/(.*)`** responses include **`x-vercel-enable-rewrite-caching: 0`** to reduce undesired caching of authenticated GETs.

### Local dev

- **`frontend/vite.config.ts`**: dev server proxies **`/api`** → **`http://127.0.0.1:8080`** with path rewrite stripping the **`/api`** prefix so local backend receives **`/`**-relative routes as implemented.

**Important:** Frontend routing correctness does **not** fix DB connectivity; a broken **`DATABASE_URL` path inside ECS** still breaks **`/register`**, **`/history`**, webhook, etc., while **`GET /`** on ECS may still be OK.

---

## 7. Supabase-specific notes

- Connection strings typically use host **`db.<project-ref>.supabase.co`** (direct DB).
- Supabase also offers **connection pooling** (PgBouncer) with **different hostnames** — sometimes preferable for server-side apps and worth testing if direct **`db.`** host causes resolver or TLS edge cases.
- Ensure **`sslmode=require`** (or stricter) matches Supabase expectations.

**Schema alignment:** `backend/sql/supabase_align_schema.sql` may exist for DDL alignment — confirm separately from networking.

---

## 8. Debugging checklist for the assigned agent

1. **CloudWatch logs (new task after deploy)**  
   - Confirm **`database engine: ... hostaddr_set=`**  
   - If **`False`**: IPv4 path failed — check VPC egress to **`dns.google:443`**, resolver behavior, or set **`DATABASE_HOSTADDR`** temporarily from a known-good **`nslookup db.<project>.supabase.co 8.8.8.8`** (A record).

2. **Stale tasks**  
   - ECS → **`default`** cluster → **`nila-api`** → confirm **new deployment** is **PRIMARY** and tasks use **new deployment ID**.

3. **`DATABASE_URL` actually set on running task**  
   - Compare task definition / console env with Supabase dashboard string (no secrets in logs — use “present / length / host fragment only”).

4. **Reproduce inside task**  
   - ECS Exec (if enabled) or one-off debug task in same subnets/security groups: `python -c` or `psql` with explicit **`hostaddr`** vs without.

5. **SQLAlchemy / psycopg2 behavior**  
   - If **`hostaddr_set=True`** but IPv6 still appears in errors, trace **`create_engine` → connect_args → psycopg2.connect** (possible driver ignores **`hostaddr`** in some combinations — verify against SQLAlchemy + psycopg2 docs for the pinned versions in **`backend/requirements.txt`**).

6. **Infrastructure alternatives**  
   - Enable **IPv6 egress** end-to-end on subnets + task networking so **AAAA** works without hacks.  
   - Use **Supabase pooler** connection string.  
   - Move DB to **RDS** inside VPC with private connectivity if Supabase edge networking remains problematic.

---

## 9. Key file paths (quick index)

| Path | Relevance |
|------|-----------|
| `backend/database.py` | URL normalization, IPv4 / `hostaddr`, engine creation |
| `backend/main.py` | FastAPI routes; **`Depends(get_db)`** usage |
| `backend/Dockerfile` | Image build, port 8080 |
| `backend/requirements.txt` | **`sqlalchemy`**, **`psycopg2`** versions |
| `backend/aws/deploy.ps1` | Build, ECR push, CFN deploy, ECS forced rollout |
| `backend/aws/cloudformation/01-base.yaml` | ECR + IAM |
| `backend/aws/cloudformation/02-ecs-express.yaml` | ECS Express service + **`DATABASE_URL`** wiring |
| `frontend/vercel.json` | **`/api`** rewrite to ECS |
| `frontend/src/config.ts` | **`API_URL`** default **`/api`** |
| `frontend/vite.config.ts` | Local **`/api`** proxy |
| `docs/founder-actions.md` | Short **Infrastructure notes** on IPv6 / Supabase / Fargate |

---

## 10. Definition of done

- ECS tasks log **`hostaddr_set=True`** (or document intentional IPv6-only path).
- **`POST /register`** or **`POST /token`** succeeds against **Supabase Postgres** (no **`Network is unreachable`**).
- Optional: **`/telegram/webhook`** processes without DB **`OperationalError`**.

---

## 11. Constraints / etiquette for the agent

- Do **not** commit secrets; rotate anything accidentally pasted.
- Prefer **minimal, reversible** infra changes; document any CFN or Supabase setting changes.
- After fixing connectivity, ensure **`deploy.ps1`** workflow still builds and **`force-new-deployment`** remains documented if `:latest` digest-only updates recur.

---

*Prepared as a single handoff artifact so another agent can continue without relying on prior chat threads.*
