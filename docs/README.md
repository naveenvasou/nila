# Nila — documentation

## For everyone

| Document | Description |
|----------|-------------|
| [**Product guide (what Nila is)**](./PRODUCT.md) | Experience, identity, personality, language (incl. Tanglish), texting style, romantic arc phases, what’s configurable vs fixed, boundaries |

## For builders

Nila is a full-stack chat web app: a React (Vite) frontend talks to a FastAPI backend that uses **Google Gemini** for replies, **SQLAlchemy** for users and message history, and **JWT** authentication.

| Document | Contents |
|----------|----------|
| [Backend](./backend.md) | Tech stack, modules, API routes, auth, DB, LLM behavior, env vars |
| [Frontend](./frontend.md) | Routes, UI flow, API client, build, Vercel, local dev |
| [Deployment](./deployment.md) | AWS (ECR, ECS Express Mode), CloudFormation stacks, deploy script, secrets, CORS |

Product and engineering docs cross-link where useful (e.g. persona brief vs `SYSTEM_INSTRUCTION` in code).
