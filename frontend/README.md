# AerOS Frontend

React SPA for **AerOS by Prakersh**. See the [root README](../README.md) for
the full product overview and one-command setup (`./app.sh start`).

## Stack

- **React 19** + **TypeScript** (`@` aliases `src/`)
- **Vite** dev server / build
- **Tailwind CSS v4** (`@tailwindcss/vite`), dark theme
- **TanStack Query** for server state, **Zustand** for auth state
- **React Router 7** — role-based portals (buyer / vendor / admin)
- **Playwright** for E2E

## Run

```bash
pnpm install      # or: npm install
pnpm dev          # http://localhost:5173
pnpm build        # production build -> dist/
pnpm preview      # serve the built bundle
```

The dev server proxies `/api` and `/ws` to the backend at
`http://localhost:4040` (see `vite.config.ts`), so run the backend alongside it.

## Tests

```bash
pnpm exec playwright test                              # E2E suite (e2e/*.spec.ts)
pnpm exec playwright test --config=playwright.demo.config.ts   # demo video capture
```

- `e2e/` — auth, buyer, vendor, admin, and RFx-lifecycle flows; shared
  `helpers.ts` logs in as the seeded demo accounts.
- `e2e/demo/` — slow-motion, video-recording specs used to produce demo clips.

## Notable UI

- **AgentBlocks** (`src/components/ui/AgentBlocks.tsx`) renders the chat
  co-pilot's structured responses (text, table, card, key-value, list, actions)
  from the backend's typed block payload — XSS-safe, no raw HTML.
- Three role shells (Buyer / Vendor / Admin) gated by a `ProtectedRoute`.
