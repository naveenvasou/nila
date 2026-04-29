# Backend — Nila API

For **what Nila is as a product** (persona, texting style, romantic arc, boundaries), see [Product guide](./PRODUCT.md). This page is technical.

The backend lives under **`backend/`**. It is a **FastAPI** application exposed with **Uvicorn**, packaged as a **Docker** image for cloud deploys.

## Technology stack

| Layer | Choice |
|--------|--------|
| Runtime | Python 3.12 (see `Dockerfile`) |
| Web framework | FastAPI |
| ASGI server | Uvicorn (`main:app`) |
| DB ORM | SQLAlchemy 2.x-style patterns (`declarative_base`, `sessionmaker`) |
| DB drivers | SQLite (dev default) or **psycopg2** for Postgres (`requirements.txt`) |
| Auth | JWT (`python-jose`), password hashing (`bcrypt`) |
| LLM | **Google GenAI** client (`google-genai`), model `gemini-3-flash-preview` |
| Config | `python-dotenv` (`load_dotenv()` in `main.py`) |

## Source layout

| File | Responsibility |
|------|----------------|
| `main.py` | App factory, CORS, routes, Gemini client, system prompt, chat orchestration |
| `database.py` | `SQLALCHEMY_DATABASE_URL`, engine, `SessionLocal`, `get_db` dependency |
| `models.py` | SQLAlchemy models `User`, `Message` |
| `auth.py` | `SECRET_KEY`, JWT encode/decode, password hash/verify |
| `requirements.txt` | Python dependencies |
| `Dockerfile` | Container image: installs deps, sets `PORT=8080`, runs Uvicorn |
| `.env` / `.env.example` | Local secrets (not committed); example lists `GEMINI_API_KEY` |

## Data model

Defined in `models.py`:

- **`users`**
  - `id` (PK), `username` (unique), `hashed_password`
  - One-to-many: `messages`

- **`messages`**
  - `id` (PK), `content`, `role`, `timestamp`, `user_id` (FK → `users.id`)
  - **`role`**: application code uses **`"user"`** for human messages and **`"model"`** for assistant/Gemini messages (the column comment in `models.py` may say `'nila'` historically; persisted values follow the code paths in `main.py`).

Tables are created at startup via `Base.metadata.create_all(bind=engine)` in `main.py`.

## Database configuration (`database.py`)

- **`DATABASE_URL`** (optional env): If set and non-empty after strip, used as the SQLAlchemy URL.
- If unset or empty: defaults to **`sqlite:///./nila.db`** (file relative to process working directory — inside the container this is typically `/app`).

**SQLite in containers** (e.g. default ECS task): data is **ephemeral** across redeploys unless you mount a volume or switch to Postgres.

**Postgres (e.g. RDS)**: set `DATABASE_URL` to a full URL. For RDS, include TLS as required (e.g. `?sslmode=require` in the URL). SQLAlchemy `connect_args` only special-cases SQLite (`check_same_thread`).

## Authentication (`auth.py`)

- **`SECRET_KEY`**: env var; JWT signing. Default in code is a placeholder — **must** be set in production (CloudFormation passes `SECRET_KEY` into the container on AWS).
- **`ALGORITHM`**: `HS256`
- **`ACCESS_TOKEN_EXPIRE_MINUTES`**: `30` (used when issuing tokens on register/login)
- Passwords: **bcrypt** with generated salt

**Note:** Local `.env` may use `JWT_SECRET_KEY`; the AWS deploy script maps `JWT_SECRET_KEY` → `SECRET_KEY` if `SECRET_KEY` is missing so the same file can feed both conventions.

## CORS (`main.py`)

- **`CORS_ORIGINS`** env: comma-separated list of allowed browser origins. If non-empty, **only** those origins are allowed (plus parsing strips whitespace).
- If **`CORS_ORIGINS`** is empty: a built-in **`_default_origins`** list is used (Vercel hostnames, custom domain, localhost — see `main.py` for the current list).

Middleware: `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]`.

Any new production frontend URL must be either added to defaults in code **or** included in `CORS_ORIGINS` on the running service (see [Deployment](./deployment.md)).

## HTTP API

Base URL is whatever host serves `main.py` (local `http://127.0.0.1:8000`, or HTTPS on AWS). Paths below are **relative** to that origin.

### Public / health

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/` | None | JSON health: `{"status":"Nila Backend is running (Auth Enabled)"}` |
| `GET` | `/docs` | None | FastAPI Swagger UI (if not disabled) |

### Auth and users

| Method | Path | Auth | Body | Response |
|--------|------|------|------|----------|
| `POST` | `/register` | None | JSON `{"username","password"}` | `Token`: `access_token`, `token_type` |
| `POST` | `/token` | None | OAuth2 form: `username`, `password` (`application/x-www-form-urlencoded`) | `Token` |

`OAuth2PasswordBearer` in `main.py` uses **`tokenUrl="token"`** (clients should POST credentials to `/token`).

### Authenticated chat

| Method | Path | Auth | Body | Response |
|--------|------|------|------|----------|
| `GET` | `/history` | `Authorization: Bearer <jwt>` | — | `MessageHistoryItem[]`: `id`, `text`, `sender` (`"user"` \| `"nila"`), `time` |
| `POST` | `/chat` | `Authorization: Bearer <jwt>` | JSON `{"message": string}` | `ChatResponse`: `messages: string[]` |

**History mapping:** DB `role == "model"` is exposed to the client as **`sender: "nila"`**; `"user"` stays `"user"`.

### Chat pipeline (`POST /chat`)

1. Persists the user message (`role="user"`).
2. Loads up to **20** most recent messages for that user (ordered for model context).
3. Builds Gemini **`contents`**: each turn is `types.Content` with role `user` or `model`; user/model text is prefixed with a **timestamp** `[YYYY-MM-DD HH:MM]` for time awareness (not stored as separate fields in DB for the model text prefix).
4. Calls `client.models.generate_content` with:
   - **`model`**: `gemini-3-flash-preview`
   - **`system_instruction`**: large in-app persona string (`SYSTEM_INSTRUCTION` — character, Tanglish, multi-bubble `|` delimiter rules, etc.)
   - **`temperature`**: `0.9`
5. Splits assistant `response.text` on **`|`** into multiple bubbles; trims; falls back to whole text if empty splits.
6. Persists each bubble as a separate `Message` with `role="model"`.
7. Returns `{ "messages": [...] }`.

If **`GEMINI_API_KEY`** is missing, `client` is `None` and `/chat` returns **500** with `"Gemini API Key not configured"`.

## Environment variables (reference)

| Variable | Required | Purpose |
|----------|----------|---------|
| `GEMINI_API_KEY` | Yes (for chat) | Google AI API key for GenAI client |
| `SECRET_KEY` | Yes (production) | JWT signing secret |
| `DATABASE_URL` | No | Postgres (or other) URL; empty → SQLite |
| `CORS_ORIGINS` | No | Overrides default allowed origins when set |
| `PORT` | No (default in Docker `8080`) | Uvicorn listen port (`Dockerfile` / orchestrator) |

## Docker

- **Image**: `python:3.12-slim`; installs `libpq-dev` and `gcc` for **psycopg2**.
- **CMD**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

## Known limitations / operations notes

- **Ephemeral SQLite** on Fargate/ECS without a volume: users/messages can reset on redeployment.
- **JWT secret rotation**: Changing `SECRET_KEY` invalidates existing tokens; users must log in again.
- **Model name** is hardcoded in `main.py`; changing Gemini model requires a code edit and redeploy.

## Related docs

- [Frontend](./frontend.md) — how the SPA calls these endpoints.
- [Deployment](./deployment.md) — ECR image, ECS Express, env injection, CloudFormation.
