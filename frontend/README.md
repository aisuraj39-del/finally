# FinAlly Frontend

Next.js (App Router, TypeScript, Tailwind v4) built as a **static export** and served by FastAPI on the same origin. See `planning/PLAN.md` §10 for the spec and §8 for the API contract.

## Develop

```bash
# Terminal 1: backend on :8000
cd backend && uv run uvicorn app.main:app --reload

# Terminal 2: frontend on :3000; /api/* is proxied to :8000 (BACKEND_URL to override)
cd frontend && npm install && npm run dev
```

## Build, test, lint

```bash
npm run build   # static export -> out/ (copied to the backend's static/ dir in Docker)
npm test        # Vitest + React Testing Library
npm run lint
```

## Structure

- `src/app/page.tsx`: the single page: `PriceProvider` + `Workstation`
- `src/components/`: panels (Watchlist, MainChart, Heatmap, PnLChart, PositionsTable, TradeBar, ChatPanel, Header)
- `src/lib/priceStore.ts`: the one `EventSource` to `/api/stream/prices`; latest ticks, per-ticker history since page load, connection status
- `src/lib/portfolio.ts`: live valuation (holdings from `/api/portfolio` × streamed prices)
- `src/lib/api.ts`: REST client; errors surface as `ApiError(code, message)`
- `src/lib/colors.ts`: up/down colors validated for color-vision deficiency; heatmap diverging scale
