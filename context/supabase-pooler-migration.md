# Supabase Pooler Migration & IPv6 Connectivity Fix

**Date:** 2026-04-30  
**Status:** Resolved  
**Symptom:** `psycopg2.OperationalError: connection to server at "db.<project>.supabase.co" ... (IPv6 address) ... Network is unreachable`

---

## The Problem

Supabase removed IPv4 from the direct database host `db.<project>.supabase.co` — it now publishes **only AAAA (IPv6)** records unless you've paid for an IPv4 add-on.

**Why it broke on ECS Express / Fargate:**
- ECS Express subnets have **no working IPv6 egress** by default.
- psycopg2 / libpq resolved the hostname to AAAA, attempted to connect over IPv6, hit "Network is unreachable".
- Meanwhile, `GET /` (health check) succeeded because it doesn't touch the DB.

---

## The Solution: Supabase Supavisor Pooler

**Switch `DATABASE_URL` to the transaction-mode connection pooler:**

```
postgresql://postgres.<project-ref>:<password>@aws-1-<region>.pooler.supabase.com:6543/postgres?sslmode=require
```

**Key differences from direct DB host:**
| Aspect | Direct `db.` | Pooler |
|--------|---|---|
| Hostname | `db.<ref>.supabase.co` | `aws-1-<region>.pooler.supabase.com` |
| Port | 5432 | 6543 (transaction mode) or 5432 (session mode) |
| Username | `postgres` | `postgres.<ref>` |
| A records | ❌ None (IPv4-only users blocked) | ✅ Yes (pooler = IPv4) |
| For | Direct connections, PgAdmin, dev | Server-side apps, serverless, Fargate |

**Get the exact pooler URL:**
1. Supabase Dashboard → Project Settings → Database → Connection string
2. Select **Connection pooling** → **Transaction** tab → **URI**
3. Copy and paste into `D:\nila\.env` or `D:\nila\backend\.env` as `DATABASE_URL=...`

---

## Critical: URL-Safe Password Encoding

If the DB password contains any of these characters, they **must be percent-encoded** in the URL:

| Character | Encode as |
|-----------|-----------|
| `#` | `%23` |
| `@` | `%40` |
| `:` | `%3A` |
| `/` | `%2F` |
| `?` | `%3F` |
| `%` | `%25` |
| space | `%20` |

**Example:**
- Raw password: `nilaAI0814#`
- In `DATABASE_URL`: `nilaAI0814%23`

This is **non-negotiable** — URL parsers will silently truncate the string at the unencoded character, breaking the connection.

---

## Deployment Checklist

After updating `DATABASE_URL`:

1. **Verify in `.env`** — run `Get-Content D:\nila\.env | Select-String DATABASE_URL` to confirm it's there.
2. **Run deploy script** — `cd D:\nila\backend\aws && .\deploy.ps1`
3. **Verify task env** — AWS Console → ECS → default cluster → nila-api service → Tasks tab → click task → check **Environment** section has the pooler URL.
4. **Test DB endpoints** — hit `POST /token` with wrong creds; should return **401 "Incorrect username or password"** (not 500 / OperationalError).
5. **Check CloudWatch** — should see no `psycopg2.OperationalError` or `Network is unreachable` on `/register`, `/chat`, `/telegram/webhook`.

---

## Latency & Future Work

**Current setup:** DB in `ap-southeast-2` (Sydney), ECS in `us-east-1` (N. Virginia).  
**Impact:** ~200ms RTT per query (crosses the Pacific).  
**Solution:** Migrate ECS to `ap-southeast-2` for same-region latency. See `founder-actions.md` → P3 tasks.

---

## Dead Code to Clean Up

The old IPv4-pinning workaround in `backend/database.py` is **no longer needed**:
- `_postgres_ipv4_hostaddr()` — resolved hostname to IPv4
- `_ipv4_via_google_public_dns()` — Google DNS HTTPS fallback
- `_inject_ipv4_hostaddr_into_url()` — appended `hostaddr=<IPv4>`
- Environment variables: `DATABASE_PREFER_IPV4`, `DATABASE_HOSTADDR`, `DATABASE_IPV4_DNS_FALLBACK`
- `connect_args={"hostaddr": ...}` in SQLAlchemy engine creation

**Action:** Remove in next cleanup sprint (see `founder-actions.md` → P3 → "Remove dead IPv4-pinning code").

---

## Best Practices to Avoid This Class of Error

1. **Always use connection pooling for serverless / ephemeral workloads** (Fargate, Lambda, etc.). Direct DB connections don't scale; poolers handle connection churn.
2. **Test DB connectivity separately from app startup** — `GET /` should never be your only health check if routes depend on the DB. Test a DB-backed endpoint to confirm.
3. **URL-encode secrets in connection strings** — if it contains non-alphanumeric chars, encode it. Many tools silently fail on unencoded reserved chars.
4. **Match DB and app regions** — if your DB is in `ap-southeast-2` and your app is in `us-east-1`, you've added ~200ms to every query. Usually not intentional.
5. **Log the startup connection params** — the line `database engine: host=<hostname> hostaddr_set=True|False` helped diagnose this. Always log which DB you're actually connecting to on startup.
6. **Force task rollouts after image push** — CloudFormation may report "No changes" when only the `:latest` digest changed. Always run `aws ecs update-service ... --force-new-deployment` after pushing a new image.

---

## Related Docs

- `founder-actions.md` → Infrastructure notes — high-level context

