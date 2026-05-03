# Project context (durable memory)

Canonical, slow-moving source of truth for the Nila project. New chats and new agents should read this folder first so compacted conversation history doesn't lose meaning.

## Files

| File | Role |
|------|------|
| `AGENTS.md` | What AI assistants should read first and how to behave in this repo. |
| `product-state.md` | **Living** — current phase, shipped vs next, non-goals. |
| `DECISIONS.md` | **Living** — strategy + engineering decisions with rationale. |
| `founder-actions.md` | **Canonical** Naveen-only action queue (P0/P1/P2/P3). The copy in `docs/` is just a pointer. |
| `architecture.md` | One-page system map: components, data flow, schema, env vars. |
| `ops.md` | Runbook: deploy, rollback, CloudWatch grep cheatsheet, smoke test. |
| `supabase-pooler-migration.md` | DB connectivity (Supabase Supavisor pooler) and password encoding gotchas. |
| `claude_CEO_conversation.md` | Origin transcript: vision, positioning, early strategy. |

## Outside this folder

- **GTM canvas:** `canvases/nila-go-to-market.canvas.tsx` — open as a Cursor canvas, not raw TSX.
- **Schema log:** `backend/sql/supabase_align_schema.sql` — append `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` per change.
- **Deploy script:** `backend/aws/deploy.ps1`.

## How to keep this folder useful

- Update **`product-state.md`** when a milestone ships or priorities shift.
- Append to **`DECISIONS.md`** whenever a non-trivial choice is made (engineering or business). Keep entries to 1–3 lines + rationale.
- Add to **`founder-actions.md`** whenever execution is blocked on a real-world founder action.
- Refresh **`architecture.md`** if components, schema, or env vars change.
- Refresh **`ops.md`** if the deploy path or debugging surface changes.

If a file in `context/` disagrees with chat history, **trust the file** and confirm with the user before changing direction.

Last reorganized: 2026-05-01. **Agent stance:** see `AGENTS.md` — owner mindset, not passive assistant.
