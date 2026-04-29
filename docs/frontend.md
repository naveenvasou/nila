# Frontend — Nila SPA

The frontend lives under **`frontend/`**. It is a **React 19** single-page application built with **Vite 7** and **TypeScript**, styled with **Tailwind CSS v4**, and routed with **React Router 7**.

## Technology stack

| Area | Package / tool |
|------|------------------|
| UI | React 19, React DOM |
| Routing | `react-router-dom` |
| HTTP | `axios` |
| JWT inspection (if used) | `jwt-decode` (dependency present) |
| Build | Vite, `@vitejs/plugin-react` |
| Types | TypeScript ~5.9 |
| Lint | ESLint 9 |

## Source layout

| Path | Role |
|------|------|
| `src/main.tsx` | React root mount |
| `src/App.tsx` | `BrowserRouter`, route table |
| `src/config.ts` | **`API_URL`** — backend base URL |
| `src/Login.tsx` | Login form → `POST /token` |
| `src/Register.tsx` | Register → `POST /register` |
| `src/Chat.tsx` | Chat UI, history, send message |

Config and assets (e.g. favicons, images) may also live under `public/` per Vite conventions.

## Routing (`App.tsx`)

| Path | Component | Notes |
|------|-----------|-------|
| `/` | `<Navigate to="/chat" />` | Landing redirects to chat |
| `/login` | `Login` | |
| `/register` | `Register` | |
| `/chat` | `Chat` | Requires token in `localStorage` |

**SPA hosting:** `vercel.json` rewrites all paths to `/index.html` so direct loads of `/chat` work on Vercel.

## Backend base URL (`src/config.ts`)

The frontend resolves the API origin as:

1. **`import.meta.env.VITE_API_URL`** if defined at build time (Vite env),
2. Else a **compiled default** HTTPS URL pointing at the **AWS ECS Express** deployment (see [Deployment](./deployment.md) for how that URL is produced and updated).

**Local development:** Create `frontend/.env` (or `.env.local`) with e.g.:

```bash
VITE_API_URL=http://127.0.0.1:8000
```

Restart `npm run dev` after changing Vite env files.

**Production:** You can set `VITE_API_URL` in the Vercel project environment variables so the API base can be changed without committing a new default in `config.ts`.

## Authentication flow

- **Register** (`Register.tsx`): `POST ${API_URL}/register` with JSON `{ username, password }`. On success, stores **`access_token`** in `localStorage` under key **`token`**, navigates to `/chat`.
- **Login** (`Login.tsx`): Builds **FormData** with `username` and `password`, posts to `${API_URL}/token` with header `Content-Type: application/x-www-form-urlencoded` (axios sends form body consistent with OAuth2 password flow). Stores `token`, navigates to `/chat`.
- **Chat** (`Chat.tsx`): Reads `localStorage.getItem('token')`. If missing, redirects to `/login`. All API calls send `Authorization: Bearer <token>`.
- **401 handling:** Clears token and sends user to `/login` on unauthorized responses when loading history or sending chat.

**Storage:** Token is **not** HttpOnly; it is standard SPA localStorage — XSS on the frontend origin would be a risk; keep dependencies updated and avoid injecting untrusted HTML.

## Chat UX (`Chat.tsx`)

- On mount: `GET ${API_URL}/history` with Bearer token; maps response into local `Message[]` (`id`, `text`, `sender`, `time`).
- Send: optimistically appends user bubble; `POST ${API_URL}/chat` with `{ message }`; reads `response.data.messages` (string array).
- **Staggered bubbles:** `displayBubblesWithDelay` appends each assistant line with a random delay to mimic typing cadence; uses `|` from backend as separate logical messages (already split server-side).

## Styling

- Tailwind v4 with `@tailwindcss/postcss` (see `package.json` / postcss config if present).
- Custom tokens referenced in components include classes such as `bg-warm-bg`, `text-nila-text`, `bg-wheat-bubble`, `text-sage-accent` — defined in CSS/theme entry used by Tailwind (check `src` CSS imports and Tailwind config).

## Build and local dev

| Command | Purpose |
|---------|---------|
| `npm run dev` | Vite dev server (default port 5173) |
| `npm run build` | `tsc -b && vite build` → output in `dist/` |
| `npm run preview` | Preview production build locally |
| `npm run lint` | ESLint |

## Deployment (summary)

The production static site is typically deployed to **Vercel**. A successful CLI deploy links the directory to a Vercel **project** and team; stable aliases often follow `https://<project>-<team-slug>.vercel.app` plus any custom domains configured in the Vercel dashboard.

Details: [Deployment](./deployment.md#frontend-vercel).

## Related docs

- [Backend](./backend.md) — exact request/response shapes and auth expectations.
- [Deployment](./deployment.md) — CORS alignment between Vercel origins and the API.
