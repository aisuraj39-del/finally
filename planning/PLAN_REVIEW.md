# PLAN.md Review

> **Status (2026-10-17):** All items below have been resolved in PLAN.md. The following require code changes to the completed market data subsystem (`backend/app/market/`):
> - Add `session_open` to the cache and `session_open` / `session_change_percent` to `PriceUpdate.to_dict()` (item 3)
> - Add a 15s `: ping` keepalive to the SSE generator (item 12)
> - Create the `APIRouter` inside `create_stream_router()` (Minor)
>
> Repo housekeeping still to do: add `db/.gitkeep`, `.env.example`, a `db/finally.db` entry in `.gitignore`, and `python-dotenv` as a backend dependency.

Review of `planning/PLAN.md` against the completed market data code (`backend/app/market/`) and the current repo state. Items are ordered by impact. Resolve the "Blocking" items in PLAN.md before backend/frontend agents start in parallel.

## Blocking

### 1. Docker volume will shadow the schema directory
PLAN puts schema/seed files in `backend/db/` and mounts the runtime volume at `/app/db`. If the Dockerfile copies `backend/` to `/app` (as implied), the volume mount hides the schema files inside the container.
**Fix:** move schema into the app package (e.g. `backend/app/db/`) or mount the runtime volume elsewhere (e.g. `/data`).

### 2. Tracked tickers must include held positions
The market data source tracks "the union of all watched tickers". Removing a held ticker from the watchlist would stop its price updates (or remove it from the cache), breaking portfolio valuation and P&L.
**Fix:** define tracked tickers = watchlist ∪ open positions. Removing a ticker from the watchlist must not drop it from the data source while a position exists.

### 3. "Daily change %" has no data source
Section 10 requires daily change % in the watchlist, but `PriceUpdate.change_percent` (`backend/app/market/models.py`) is tick-to-tick. No session-open/reference price is stored.
**Fix:** decide the reference (simulator seed price / first price seen, or Massive previous close) and add it to the cache and SSE payload.

### 4. SSE payload shape differs from the plan
PLAN says "each SSE event contains ticker, price, previous price, timestamp, and change direction". Actual (`stream.py`): a single event per cycle containing a dict keyed by ticker:
```json
{"AAPL": {"ticker": "AAPL", "price": 190.5, "previous_price": 190.4,
          "timestamp": 1760700000.123, "change": 0.1,
          "change_percent": 0.0525, "direction": "up"}, ...}
```
`timestamp` is Unix seconds (float), whereas DB columns use ISO strings.
**Fix:** document this exact format in PLAN.md as the frontend contract.

### 5. No API contract (request/response shapes)
Section 8 lists endpoints but no bodies, error formats, or status codes. Parallel agents will diverge. Needed at minimum:
- `GET /api/portfolio` response (cash, positions[], total_value, unrealized P&L fields)
- `POST /api/portfolio/trade` success body and failure body/status (e.g. 400 `{"detail": "..."}`)
- `GET /api/portfolio/history` response and any range params
- `GET/POST/DELETE /api/watchlist` responses, duplicate/missing ticker behavior
- `POST /api/chat` response: message plus executed and failed actions

## Gaps (will cause guesswork)

6. **Ticker validation**: should `POST /api/watchlist` validate symbols? The simulator accepts any string; Massive silently never prices an invalid symbol. Also define trade behavior when a ticker has no cached price yet (reject).
7. **Fractional share rules**: quantity > 0, precision/rounding, and an epsilon for deleting a position when quantity reaches ~0.
8. **LLM mock behavior**: E2E "trade execution appears inline" requires a deterministic mock that returns a trade. Specify the mock responses (e.g. message containing "buy" → buy 1 AAPL).
9. **Chat history window**: how many prior messages go into the prompt.
10. **Live header total value**: frontend computes from SSE prices + positions, or polls `/api/portfolio`? Pick one.
11. **Snapshot growth**: a snapshot every 30s is ~2,900 rows/day. Add retention/downsampling or a range param on `/history`.
12. **SSE keepalive**: the stream only emits on cache version change. In Massive mode (15s polls) it is silent for long periods, so the status dot can't tell idle from dead. Emit a periodic `: ping` comment.
13. **`.env` loading locally**: `python-dotenv` is not a dependency. Running from `backend/` won't find the root `.env`. Specify the loading mechanism.

## Minor

- Not yet present in the repo: `db/.gitkeep`, `.env.example`, `frontend/`, `scripts/`, `test/`. `.gitignore` has no `db/finally.db` entry (only `db.sqlite3`).
- `stream.py` creates `router` at module level and the factory registers routes onto it. Calling `create_stream_router` twice duplicates the route. Create the router inside the factory.
- Heatmap color: P&L in dollars or percent? Specify.
- Section 11: note that the static files mount at `/` must be registered after the `/api` routes.
- `.claude/Commands/` should be `.claude/commands/` (lowercase) to work on case-sensitive filesystems.

## Recommended next step
Add an "API Contract" section to PLAN.md (JSON shapes for every endpoint plus the SSE format) and resolve items 1–3 and 6. That removes most of the cross-agent ambiguity.
