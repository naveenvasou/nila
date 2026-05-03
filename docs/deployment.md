# Deployment — AWS backend & Vercel frontend

This document reflects the **current** deployment approach in the repo: **Amazon ECS Express Mode** for the API (not AWS App Runner for new work), **Amazon ECR** for the container image, and **Vercel** for the static React app.

**Important:** Exact URLs, ARNs, and account IDs change when you recreate stacks or projects. Always confirm live values in the **AWS console** (CloudFormation outputs, ECS, ECR) and **Vercel** (Domains / Deployments).

## Architecture overview

```
[Browser] → HTTPS → Vercel (React SPA)
                ↓ API calls (HTTPS + JWT)
            AWS ALB (managed by ECS Express)
                ↓
            Fargate task(s) running Docker image from ECR
                ↓
            Optional: RDS Postgres if DATABASE_URL set; else SQLite in container
                ↓
            Google Gemini API (GEMINI_API_KEY)
```

## AWS account prerequisites

- **AWS CLI v2** configured (`aws configure` or environment credentials).
- **Docker Desktop** (or compatible engine) for **`backend/aws/deploy.ps1`** image build/push.
- **IAM permissions** to deploy CloudFormation, ECR, ECS Express–related resources, and (first ECS use) ensure the **ECS service-linked role** exists:  
  `AWSServiceRoleForECS` (created automatically on first ECS use, or via `aws iam create-service-linked-role --aws-service-name ecs.amazonaws.com`).
- **Region:** Scripts default to **`us-east-1`**. ECS Express and ECR must be in a region where those services are available.

## Backend — repository layout

| Path | Purpose |
|------|---------|
| `backend/Dockerfile` | Production image |
| `backend/aws/deploy.ps1` | End-to-end deploy: base stack → Docker build/push → app stack |
| `backend/aws/cloudformation/01-base.yaml` | Stack **`nila-aws-base`**: ECR + IAM for ECS Express |
| `backend/aws/cloudformation/02-ecs-express.yaml` | Stack **`nila-aws-app`**: `AWS::ECS::ExpressGatewayService` |

## CloudFormation stack 1: `nila-aws-base`

**Template:** `backend/aws/cloudformation/01-base.yaml`  
**Stack name:** `nila-aws-base` (default in `deploy.ps1`)

**Creates:**

- **ECR repository** (default name `nila-backend`, overridable via parameter `RepositoryName`).
- **`EcsTaskExecutionRole`**: trust **`ecs-tasks.amazonaws.com`**, managed policy **`AmazonECSTaskExecutionRolePolicy`** (pull from ECR, CloudWatch logs, etc.).
- **`EcsExpressInfrastructureRole`**: trust **`ecs.amazonaws.com`**, managed policy **`AmazonECSInfrastructureRoleforExpressGatewayServices`** (ECS Express creates/manages ALB, target groups, security groups, etc.).

**Outputs (used by stack 2 / script):**

- `RepositoryUri`, `EcrImageUri` (…`/nila-backend:latest`),
- `EcsTaskExecutionRoleArn`,
- `EcsExpressInfrastructureRoleArn`.

**Deploy:** Included in `deploy.ps1` with `--capabilities CAPABILITY_NAMED_IAM`.

## CloudFormation stack 2: `nila-aws-app`

**Template:** `backend/aws/cloudformation/02-ecs-express.yaml`  
**Stack name:** `nila-aws-app`

**Creates:**

- **`AWS::ECS::ExpressGatewayService`** logical ID `NilaExpressApi`.
- **Service name:** `nila-api` (ECS service name).
- **Task resources:** `Cpu: "256"` (0.25 vCPU Fargate units), `Memory: "512"` (MiB).
- **Container:** image from parameter `EcrImageUri`, port **8080**, health check path **`/`**.
- **Environment variables** passed into the container:
  - `PORT=8080`
  - `GEMINI_API_KEY`
  - `SECRET_KEY`
  - `CORS_ORIGINS` (comma-separated; empty string → app uses code defaults in `main.py`)
  - `DATABASE_URL` (empty → SQLite in container)
  - `TELEGRAM_BOT_TOKEN` (empty → Telegram `sendMessage` / webhook registration cannot run)
  - `BACKEND_BASE_URL` (public `https://…` API origin; used on startup to register the Telegram webhook)

**Scaling:** `ScalingTarget` — `MinTaskCount: 1`, `MaxTaskCount: 2`, metric **`AVERAGE_CPU`**, target **70**.

**Outputs:**

- `ServiceArn` — ECS Express service ARN.
- `ApiEndpoint` — hostname (or URL) for HTTPS access. The public URL typically follows the documented ECS pattern: `https://<name>.ecs.<region>.on.aws` (confirm in stack output and AWS console).

## Deploy script (`backend/aws/deploy.ps1`)

**Usage (PowerShell):**

```powershell
cd path\to\repo\backend\aws
$env:GEMINI_API_KEY = "..."
$env:SECRET_KEY = "..."   # or rely on backend\.env below
# Optional:
# $env:AWS_REGION = "us-east-1"
# $env:CORS_ORIGINS = "https://your-frontend.vercel.app,http://localhost:5173"
# $env:DATABASE_URL = "postgresql://...?sslmode=require"
# $env:TELEGRAM_BOT_TOKEN = "..."
# $env:BACKEND_BASE_URL = "https://<ApiEndpoint-from-stack>"
.\deploy.ps1
```

**Behavior:**

1. Verifies `aws` and `docker` on `PATH`.
2. Loads **repo root `.env`** then **`backend/.env`** into a merged map (**backend wins** on duplicate keys). Applies each key to the process environment only when that variable is unset or blank in the shell (explicit shell exports always win). Also maps `JWT_SECRET_KEY` → `SECRET_KEY` when `SECRET_KEY` is still unset after merge.
3. Fails if `GEMINI_API_KEY` or `SECRET_KEY` still missing. Warns if `TELEGRAM_BOT_TOKEN` or `DATABASE_URL` missing.
4. Deploys / updates **`nila-aws-base`**.
5. Reads ECR URI and both ECS role ARNs from stack outputs.
6. `docker login` to ECR, **`docker build`** from **`backend/`** (`$Root`), tag and **`docker push`** `:latest`.
7. Writes a temporary JSON parameter file (UTF-8 no BOM) and runs **`aws cloudformation deploy`** for **`nila-aws-app`** with **`--parameter-overrides file://<absolute-path>`** (Windows path style required by AWS CLI on Windows).
8. Prints the API base URL from **`ApiEndpoint`**.

**Updating only configuration (no code change):** You can run `aws cloudformation deploy` again with the same template and a new parameter set (e.g. wider `CORS_ORIGINS`) without rebuilding the image if only env vars change — the template passes env into the Express service.

**When Docker/ECR is flaky:** If the image is already in ECR, you can deploy stack 2 alone by supplying the same parameters as `deploy.ps1` (see generated `._cfn_param_overrides.json` pattern in the script).

**Telegram webhook:** After deploy, register the webhook once (replace `<TOKEN>` from BotFather):

```powershell
curl.exe -s "https://api.telegram.org/bot<TOKEN>/setWebhook" -d "url=https://<ApiEndpoint-from-stack-output>/telegram/webhook"
```

The HTTP API process **does not** call Telegram during startup (that previously delayed health checks and tripped the ECS deployment circuit breaker).

## Container runtime

- **Entrypoint:** Uvicorn serves `main:app` on `0.0.0.0:$PORT`.
- **Health check:** ECS Express uses **`GET /`** against the service (must return success for ALB health).

## Secrets and security

- **Never commit** repo root `.env` or `backend/.env` with real keys.
- CloudFormation parameters **`GeminiApiKey`** and **`SecretKey`** use **`NoEcho: true`** — values are still sensitive in AWS state; restrict IAM who can describe stacks/parameters.
- **Rotate** `GEMINI_API_KEY` and `SECRET_KEY` if ever exposed; after rotation, update stack parameters or `.env` and redeploy.

## CORS vs Vercel URLs

The backend must list every **browser origin** that will call the API (scheme + host + port). Sources of truth:

1. **`CORS_ORIGINS`** on the ECS task (from CloudFormation parameter), **or**
2. **`_default_origins`** in `main.py` when `CORS_ORIGINS` is empty.

When you add a new Vercel production hostname or custom domain, either:

- extend `CORS_ORIGINS` in the next **`nila-aws-app`** deploy, **or**
- extend `_default_origins` and rebuild/push the image.

Mismatch symptoms: browser blocks requests with CORS errors; API otherwise healthy from `curl`.

## Frontend — Vercel

**Project:** Typically linked under a team such as `naveens-projects-31cb48a9` with project name **`frontend`** (`.vercel/project.json` after `vercel link` / deploy).

**Deploy:**

```bash
cd frontend
npm run build    # optional local check
npx vercel deploy --prod
```

**Routing:** `frontend/vercel.json` rewrites all paths to `/index.html` for SPA deep links (e.g. `/chat`).

**API URL:** See `frontend/src/config.ts` — `VITE_API_URL` overrides compiled default.

**Multiple Vercel URLs:** A legacy project might still exist at e.g. `nila-ashy.vercel.app` while CLI deploys target the `frontend` project’s aliases. Align domains in the Vercel dashboard if you want a single canonical hostname.

## Cost and ops notes (high level)

- **ECS Express:** No extra “Express” fee; you pay for **Fargate** tasks, **Application Load Balancer**, data transfer, **CloudWatch** logs, etc. **Shared ALB** across multiple Express services can reduce per-service ALB cost ([AWS: ECS Express overview](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/express-service-overview.html)).
- **App Runner:** AWS has announced **no new App Runner customers after April 30, 2026**; existing services continue. New container deployments in AWS should use paths such as **ECS Express** ([AWS announcement context](https://docs.aws.amazon.com/apprunner/latest/dg/what-is-apprunner.html)) — this repo’s templates follow that direction.

## Troubleshooting quick reference

| Symptom | Check |
|---------|--------|
| CloudFormation fails on ECS Express with service-linked role | `AWSServiceRoleForECS` exists in IAM |
| ECR push TLS timeout | Retry; verify network/VPN; push when stable |
| CORS errors from browser | Origin in `CORS_ORIGINS` or `_default_origins`; HTTPS vs HTTP mismatch |
| 401 on `/history` / `/chat` | Token in `localStorage`, `SECRET_KEY` unchanged since token issued |
| 500 on `/chat` “Gemini API Key not configured” | `GEMINI_API_KEY` on task / local `.env` |
| Empty DB after deploy | SQLite in container without volume — expected; use RDS + `DATABASE_URL` |

## Related docs

- [Backend](./backend.md) — API and env reference.
- [Frontend](./frontend.md) — how the app picks `API_URL`.
- [README](./README.md) — doc index.
