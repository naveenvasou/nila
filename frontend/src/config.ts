/**
 * API requests default to same-origin `/api` so the browser never resolves the ECS hostname.
 * Vercel rewrites `/api/*` → ECS (see vercel.json). Local dev uses Vite proxy (vite.config.ts).
 * Set VITE_API_URL only when you need to hit the API directly (e.g. full HTTPS URL).
 */
function normalizedExplicit(): string | undefined {
  const raw = import.meta.env.VITE_API_URL;
  if (raw === undefined || raw === null) return undefined;
  const s = String(raw).trim();
  if (!s) return undefined;
  return s.replace(/\/+$/, "");
}

const explicit = normalizedExplicit();

export const API_URL = explicit ?? "/api";
