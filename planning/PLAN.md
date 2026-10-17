# FinAlly — AI Trading Workstation

## Project Specification

## 1. Vision

FinAlly (Finance Ally) is a visually stunning AI-powered trading workstation that streams live market data, lets users trade a simulated portfolio, and integrates an LLM chat assistant that can analyze positions and execute trades on the user's behalf. It looks and feels like a modern Bloomberg terminal with an AI copilot.

This is the capstone project for an agentic AI coding course. It is built entirely by Coding Agents demonstrating how orchestrated AI agents can produce a production-quality full-stack application. Agents interact through files in `planning/`.

## 2. User Experience

### First Launch

The user runs a single Docker command (or a provided start script). A browser opens to `http://localhost:8000`. No login, no signup. They immediately see:

- A watchlist of 10 default tickers with live-updating prices in a grid
- $10,000 in virtual cash
- A dark, data-rich trading terminal aesthetic
- An AI chat panel ready to assist

### What the User Can Do

- **Watch prices stream** — prices flash green (uptick) or red (downtick) with subtle CSS animations that fade
- **View sparkline mini-charts** — price action beside each ticker in the watchlist, accumulated on the frontend from the SSE stream since page load (sparklines fill in progressively)
- **Click a ticker** to see a larger detailed chart in the main chart area
- **Buy and sell shares** — market orders only, instant fill at current price, no fees, no confirmation dialog
- **Monitor their portfolio** — a heatmap (treemap) showing positions sized by weight and colored by P&L, plus a P&L chart tracking total portfolio value over time
- **View a positions table** — ticker, quantity, average cost, current price, unrealized P&L, % change
- **Chat with the AI assistant** — ask about their portfolio, get analysis, and have the AI execute trades and manage the watchlist through natural language
- **Manage the watchlist** — add/remove tickers manually or via the AI chat

### Visual Design

- **Dark theme**: backgrounds around `#0d1117` or `#1a1a2e`, muted gray borders, no pure black
- **Price flash animations**: brief green/red background highlight on price change, fading over ~500ms via CSS transitions
- **Connection status indicator**: a small colored dot (green = connected, yellow = reconnecting, red = disconnected) visible in the header
- **Professional, data-dense layout**: inspired by Bloomberg/trading terminals — every pixel earns its place
- **Responsive but desktop-first**: optimized for wide screens, functional on tablet

### Color Scheme
- Accent Yellow: `#ecad0a`
- Blue Primary: `#209dd7`
- Purple Secondary: `#753991` (submit buttons)

## 3. Architecture Overview

### Single Container, Single Port

```
┌─────────────────────────────────────────────────┐
│  Docker Container (port 8000)                   │
│                                                 │
│  FastAPI (Python/uv)                            │
│  ├── /api/*          REST endpoints             │
│  ├── /api/stream/*   SSE streaming              │
│  └── /*              Static file serving         │
│                      (Next.js export)            │
│                                                 │
│  SQLite database (volume-mounted)               │
│  Background task: market data polling/sim        │
└─────────────────────────────────────────────────┘
```

- **Frontend**: Next.js with TypeScript, built as a static export (`output: 'export'`), served by FastAPI as static files
- **Backend**: FastAPI (Python), managed as a `uv` project
- **Database**: SQLite, single file at `db/finally.db`, volume-mounted for persistence
- **Real-time data**: Server-Sent Events (SSE) — simpler than WebSockets, one-way server→client push, works everywhere
- **AI integration**: LiteLLM → OpenRouter (Cerebras for fast inference), with structured outputs for trade execution
- **Market data**: Environment-variable driven — simulator by default, real data via Massive API if key provided

### Why These Choices

| Decision | Rationale |
|---|---|
| SSE over WebSockets | One-way push is all we need; simpler, no bidirectional complexity, universal browser support |
| Static Next.js export | Single origin, no CORS issues, one port, one container, simple deployment |
| SQLite over Postgres | No auth = no multi-user = no need for a database server; self-contained, zero config |
| Single Docker container | Students run one command; no docker-compose for production, no service orchestration |
| uv for Python | Fast, modern Python project management; reproducible lockfile; what students should learn |
| Market orders only | Eliminates order book, limit order logic, partial fills — dramatically simpler portfolio math |

---

## 4. Directory Structure

```
finally/
├── frontend/                 # Next.js TypeScript project (static export)
├── backend/                  # FastAPI uv project (Python)
│   └── app/
│       ├── market/           # Market data subsystem (complete)
│       └── db/               # Schema definitions, seed data, migration logic
├── planning/                 # Project-wide documentation for agents
│   ├── PLAN.md               # This document
│   └── ...                   # Additional agent reference docs
├── scripts/
│   ├── start_mac.sh          # Launch Docker container (macOS/Linux)
│   ├── stop_mac.sh           # Stop Docker container (macOS/Linux)
│   ├── start_windows.ps1     # Launch Docker container (Windows PowerShell)
│   └── stop_windows.ps1      # Stop Docker container (Windows PowerShell)
├── test/                     # Playwright E2E tests + docker-compose.test.yml
├── db/                       # Volume mount target (SQLite file lives here at runtime)
│   └── .gitkeep              # Directory exists in repo; finally.db is gitignored
├── Dockerfile                # Multi-stage build (Node → Python)
├── docker-compose.yml        # Optional convenience wrapper
├── .env                      # Environment variables (gitignored, .env.example committed)
└── .gitignore
```

### Key Boundaries

- **`frontend/`** is a self-contained Next.js project. It knows nothing about Python. It talks to the backend via `/api/*` endpoints and `/api/stream/*` SSE endpoints. Internal structure is up to the Frontend Engineer agent.
- **`backend/`** is a self-contained uv project with its own `pyproject.toml`. It owns all server logic including database initialization, schema, seed data, API routes, SSE streaming, market data, and LLM integration. Internal structure is up to the Backend/Market Data agents.
- **`backend/app/db/`** contains schema SQL definitions and seed logic. It lives inside the `app` package (not `backend/db/`) so that it is never shadowed by the runtime volume mounted at `/app/db` in the container. The backend lazily initializes the database on first request — creating tables and seeding default data if the SQLite file doesn't exist or is empty.
- **`db/`** at the top level is the runtime volume mount point and contains only data, never code. The SQLite file (`db/finally.db`) is created here by the backend and persists across container restarts via Docker volume. The DB path is resolved from the `DB_PATH` env var, defaulting to `<project root>/db/finally.db` locally and `/app/db/finally.db` in the container. `db/finally.db` must be listed in `.gitignore`.
- **`planning/`** contains project-wide documentation, including this plan. All agents reference files here as the shared contract.
- **`test/`** contains Playwright E2E tests and supporting infrastructure (e.g., `docker-compose.test.yml`). Unit tests live within `frontend/` and `backend/` respectively, following each framework's conventions.
- **`scripts/`** contains start/stop scripts that wrap Docker commands.

---

## 5. Environment Variables

```bash
# Required: OpenRouter API key for LLM chat functionality
OPENROUTER_API_KEY=your-openrouter-api-key-here

# Optional: Massive (Polygon.io) API key for real market data
# If not set, the built-in market simulator is used (recommended for most users)
MASSIVE_API_KEY=

# Optional: Set to "true" for deterministic mock LLM responses (testing)
LLM_MOCK=false
```

### Behavior

- If `MASSIVE_API_KEY` is set and non-empty → backend uses Massive REST API for market data
- If `MASSIVE_API_KEY` is absent or empty → backend uses the built-in market simulator
- If `LLM_MOCK=true` → backend returns deterministic mock LLM responses (for E2E tests)
- In the container, environment variables are supplied via docker `--env-file .env`; the backend does not read the file itself
- For local development, the backend loads `.env` from the project root (one level above `backend/`) using `python-dotenv` at app startup, resolving the path relative to the source file rather than the working directory. Variables already set in the environment take precedence
- A committed `.env.example` documents all variables; `.env` is gitignored

---

## 6. Market Data

### Two Implementations, One Interface

Both the simulator and the Massive client implement the same abstract interface. The backend selects which to use based on the environment variable. All downstream code (SSE streaming, price cache, frontend) is agnostic to the source.

### Simulator (Default)

- Generates prices using geometric Brownian motion (GBM) with configurable drift and volatility per ticker
- Updates at ~500ms intervals
- Correlated moves across tickers (e.g., tech stocks move together)
- Occasional random "events" — sudden 2-5% moves on a ticker for drama
- Starts from realistic seed prices (e.g., AAPL ~$190, GOOGL ~$175, etc.)
- Runs as an in-process background task — no external dependencies

### Massive API (Optional)

- REST API polling (not WebSocket) — simpler, works on all tiers
- Polls for all tracked tickers (see below) on a configurable interval
- Free tier (5 calls/min): poll every 15 seconds
- Paid tiers: poll every 2-15 seconds depending on tier
- Parses REST response into the same format as the simulator

### Shared Price Cache

- A single background task (simulator or Massive poller) writes to an in-memory price cache
- The cache holds the latest price, previous price, session open price, and timestamp for each ticker
- **Session open price** is the first price the cache records for a ticker since backend start (the seed price for the simulator, the first poll result for Massive). It is the reference for "daily change %" and is kept until the ticker is removed from the cache
- SSE streams read from this cache and push updates to connected clients
- This architecture supports future multi-user scenarios without changes to the data layer

### Tracked Tickers

The set of tickers the market data source prices is **watchlist ∪ tickers with an open position**. This guarantees every held position always has a live price for valuation and P&L.

- On startup, the source is started with the union of watchlist and position tickers
- Adding a ticker to the watchlist or buying a new ticker calls `source.add_ticker()` (idempotent)
- Removing a ticker from the watchlist calls `source.remove_ticker()` **only if** no position is held in it
- Selling a position to zero calls `source.remove_ticker()` **only if** the ticker is not on the watchlist

### Ticker Validation

- Tickers are normalized to uppercase and must match `^[A-Z][A-Z0-9.]{0,9}$`; anything else is rejected with 400
- Simulator mode: any well-formed ticker is accepted; unknown tickers get a random seed price ($50–$300) and default GBM parameters
- Massive mode: a ticker is accepted when added; if it never receives a price it simply shows no price in the watchlist and cannot be traded

### SSE Streaming

- Endpoint: `GET /api/stream/prices`
- Long-lived SSE connection; client uses native `EventSource` API
- The first message is `retry: 1000` (client reconnects after 1s on disconnect)
- Every ~500ms, if the cache has changed since the last send, the server sends **one event containing all tracked tickers**, as a JSON object keyed by ticker:

```
data: {"AAPL": {"ticker": "AAPL", "price": 190.52, "previous_price": 190.41, "session_open": 190.00, "timestamp": 1760700000.123, "change": 0.11, "change_percent": 0.0578, "session_change_percent": 0.2737, "direction": "up"}, "GOOGL": {...}}
```

| Field | Type | Meaning |
|---|---|---|
| `ticker` | string | Symbol |
| `price` | number | Latest price |
| `previous_price` | number | Price at the previous update |
| `session_open` | number | Session open price (see Shared Price Cache) |
| `timestamp` | number | **Unix seconds** (float) — not ISO, unlike REST/DB timestamps |
| `change` / `change_percent` | number | Tick-to-tick change (absolute / %) — drives flash animation |
| `session_change_percent` | number | Change vs `session_open` in % — shown as "daily change %" in the watchlist |
| `direction` | string | `"up"`, `"down"`, or `"flat"` (tick-to-tick) |

- **Keepalive**: if no data event has been sent for 15 seconds, the server sends an SSE comment line `: ping`. This keeps proxies from closing the connection and lets the frontend treat >30s of silence as disconnected (relevant in Massive mode where polls are 15s apart)
- Client handles reconnection automatically (EventSource has built-in retry)
- Implementation note: the `APIRouter` must be created inside `create_stream_router()`, not at module level, so calling the factory more than once does not register duplicate routes

---

## 7. Database

### SQLite with Lazy Initialization

The backend checks for the SQLite database on startup (or first request). If the file doesn't exist or tables are missing, it creates the schema and seeds default data. This means:

- No separate migration step
- No manual database setup
- Fresh Docker volumes start with a clean, seeded database automatically

### Schema

All tables include a `user_id` column defaulting to `"default"`. This is hardcoded for now (single-user) but enables future multi-user support without schema migration.

**users_profile** — User state (cash balance)
- `id` TEXT PRIMARY KEY (default: `"default"`)
- `cash_balance` REAL (default: `10000.0`)
- `created_at` TEXT (ISO timestamp)

**watchlist** — Tickers the user is watching
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `ticker` TEXT
- `added_at` TEXT (ISO timestamp)
- UNIQUE constraint on `(user_id, ticker)`

**positions** — Current holdings (one row per ticker per user)
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `ticker` TEXT
- `quantity` REAL (fractional shares supported)
- `avg_cost` REAL
- `updated_at` TEXT (ISO timestamp)
- UNIQUE constraint on `(user_id, ticker)`

**trades** — Trade history (append-only log)
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `ticker` TEXT
- `side` TEXT (`"buy"` or `"sell"`)
- `quantity` REAL (fractional shares supported)
- `price` REAL
- `executed_at` TEXT (ISO timestamp)

**portfolio_snapshots** — Portfolio value over time (for P&L chart). Recorded every 30 seconds by a background task, and immediately after each trade execution. Retention: snapshots older than 7 days are deleted by the same background task (keeps the table bounded at ~20k rows).
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `total_value` REAL
- `recorded_at` TEXT (ISO timestamp)

**chat_messages** — Conversation history with LLM
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `role` TEXT (`"user"` or `"assistant"`)
- `content` TEXT
- `actions` TEXT (JSON — trades executed, watchlist changes made; null for user messages)
- `created_at` TEXT (ISO timestamp)

### Default Seed Data

- One user profile: `id="default"`, `cash_balance=10000.0`
- Ten watchlist entries: AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX

### Trade Rules

These apply identically to manual trades and LLM-initiated trades.

- `quantity` must be > 0; it is rounded to 4 decimal places before execution (minimum effective quantity 0.0001)
- `side` must be `"buy"` or `"sell"`
- Execution price is the current cached price; if the ticker has no cached price, the trade is rejected (`no_price`)
- **Buy**: requires `cash_balance >= quantity × price`. New `avg_cost` = weighted average of existing and new shares
- **Sell**: requires held quantity ≥ requested quantity (with a tolerance of 1e-6). `avg_cost` is unchanged on sells; realized P&L is not tracked separately (it is reflected in cash)
- If a position's remaining quantity is < 1e-6 after a sell, the position row is deleted
- Each trade is atomic: cash update, position upsert/delete, trade log insert, and a portfolio snapshot happen in one DB transaction
- Monetary values are stored as REAL and rounded to 2 decimals only for display

---

## 8. API Endpoints

### Market Data
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/stream/prices` | SSE stream of live price updates |

### Portfolio
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/portfolio` | Current positions, cash balance, total value, unrealized P&L |
| POST | `/api/portfolio/trade` | Execute a trade: `{ticker, quantity, side}` |
| GET | `/api/portfolio/history` | Portfolio value snapshots over time (for P&L chart) |

### Watchlist
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/watchlist` | Current watchlist tickers with latest prices |
| POST | `/api/watchlist` | Add a ticker: `{ticker}` |
| DELETE | `/api/watchlist/{ticker}` | Remove a ticker |

### Chat
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/chat` | Send a message, receive complete JSON response (message + executed actions) |
| GET | `/api/chat/history` | Recent chat messages (restores the chat panel on page load) |

### System
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check (for Docker/deployment) |

### API Contract

This is the shared contract between backend and frontend. All REST bodies are JSON; all REST timestamps are ISO 8601 UTC strings. Numbers are unrounded floats.

**Errors** — every non-2xx response uses FastAPI's shape with a machine-readable code:

```json
{"detail": {"code": "insufficient_cash", "message": "Need $1,905.20, have $1,200.00"}}
```

| Code | Status | When |
|---|---|---|
| `invalid_ticker` | 400 | Ticker fails format validation |
| `invalid_quantity` | 400 | Quantity ≤ 0 or not a number |
| `invalid_side` | 400 | Side not `buy`/`sell` |
| `no_price` | 400 | No cached price for ticker |
| `insufficient_cash` | 400 | Buy exceeds cash |
| `insufficient_shares` | 400 | Sell exceeds held quantity |
| `already_watching` | 409 | Ticker already on watchlist |
| `not_watching` | 404 | Removing a ticker not on watchlist |
| `llm_error` | 502 | LLM call failed or returned unparseable output |

Request validation errors from FastAPI/Pydantic (422) may keep FastAPI's default shape.

**`GET /api/portfolio`** → 200
```json
{
  "cash_balance": 8095.0,
  "positions_value": 1952.5,
  "total_value": 10047.5,
  "unrealized_pnl": 47.5,
  "unrealized_pnl_percent": 2.49,
  "positions": [
    {"ticker": "AAPL", "quantity": 10, "avg_cost": 190.5, "current_price": 195.25,
     "market_value": 1952.5, "unrealized_pnl": 47.5, "unrealized_pnl_percent": 2.49,
     "weight": 0.1943}
  ]
}
```
`current_price` falls back to `avg_cost` if no cached price exists. `weight` = `market_value / total_value`.

**`POST /api/portfolio/trade`** — body `{"ticker": "AAPL", "quantity": 10, "side": "buy"}` → 200
```json
{
  "trade": {"id": "uuid", "ticker": "AAPL", "side": "buy", "quantity": 10, "price": 190.5, "executed_at": "2026-10-17T14:03:22Z"},
  "portfolio": { ...same shape as GET /api/portfolio... }
}
```

**`GET /api/portfolio/history?since=<ISO timestamp>`** → 200. `since` is optional; default is the last 24 hours.
```json
{"snapshots": [{"total_value": 10000.0, "recorded_at": "2026-10-17T14:00:00Z"}]}
```
Sorted ascending by `recorded_at`.

**`GET /api/watchlist`** → 200
```json
{"tickers": [{"ticker": "AAPL", "price": 190.5, "previous_price": 190.4, "session_open": 190.0,
              "session_change_percent": 0.26, "direction": "up", "added_at": "2026-10-17T13:00:00Z"}]}
```
Price fields are `null` if the ticker has no cached price yet. Sorted by `added_at`.

**`POST /api/watchlist`** — body `{"ticker": "PYPL"}` → 201 with the single entry in the same shape as one element of `tickers`.

**`DELETE /api/watchlist/{ticker}`** → 204.

**`POST /api/chat`** — body `{"message": "Buy 5 NVDA"}` → 200
```json
{
  "id": "uuid",
  "message": "Bought 5 NVDA at $875.20.",
  "actions": {
    "trades": [
      {"ticker": "NVDA", "side": "buy", "quantity": 5, "status": "executed", "price": 875.2, "error": null}
    ],
    "watchlist_changes": [
      {"ticker": "PYPL", "action": "add", "status": "failed", "error": "already_watching"}
    ]
  },
  "created_at": "2026-10-17T14:05:00Z"
}
```
`status` is `"executed"` or `"failed"`; `error` holds the error code when failed. The same `actions` object is what gets stored in `chat_messages.actions`.

**`GET /api/chat/history?limit=50`** → 200 `{"messages": [{"id", "role", "content", "actions", "created_at"}]}`, ascending. Used to restore the chat panel on page load.

**`GET /api/health`** → 200 `{"status": "ok", "market_data": "simulator" | "massive", "llm_mock": true | false}`

---

## 9. LLM Integration

When writing code to make calls to LLMs, use cerebras-inference skill to use LiteLLM via OpenRouter to the `openrouter/openai/gpt-oss-120b` model with Cerebras as the inference provider. Structured Outputs should be used to interpret the results.

There is an OPENROUTER_API_KEY in the .env file in the project root.

### How It Works

When the user sends a chat message, the backend:

1. Loads the user's current portfolio context (cash, positions with P&L, watchlist with live prices, total portfolio value)
2. Loads recent conversation history from the `chat_messages` table — the last 20 messages (10 exchanges), oldest first. Assistant messages include a short summary of their executed actions so the LLM knows what it already did
3. Constructs a prompt with a system message, portfolio context, conversation history, and the user's new message
4. Calls the LLM via LiteLLM → OpenRouter, requesting structured output, using the cerebras-inference skill
5. Parses the complete structured JSON response
6. Auto-executes any trades or watchlist changes specified in the response
7. Stores the message and executed actions in `chat_messages`
8. Returns the complete JSON response to the frontend (no token-by-token streaming — Cerebras inference is fast enough that a loading indicator is sufficient)

### Structured Output Schema

The LLM is instructed to respond with JSON matching this schema:

```json
{
  "message": "Your conversational response to the user",
  "trades": [
    {"ticker": "AAPL", "side": "buy", "quantity": 10}
  ],
  "watchlist_changes": [
    {"ticker": "PYPL", "action": "add"}
  ]
}
```

- `message` (required): The conversational text shown to the user
- `trades` (optional): Array of trades to auto-execute. Each trade goes through the same validation as manual trades (sufficient cash for buys, sufficient shares for sells)
- `watchlist_changes` (optional): Array of watchlist modifications

### Auto-Execution

Trades specified by the LLM execute automatically — no confirmation dialog. This is a deliberate design choice:
- It's a simulated environment with fake money, so the stakes are zero
- It creates an impressive, fluid demo experience
- It demonstrates agentic AI capabilities — the core theme of the course

If a trade fails validation (e.g., insufficient cash), it is reported with `status: "failed"` and an error code in the response's `actions` (see API Contract), and the frontend shows it inline. Because there is only one LLM call per message, the LLM's `message` text may have been written assuming success; the backend appends a short note to `message` for each failed action (e.g. "⚠ Buy 500 TSLA failed: insufficient cash"). Actions execute in order: watchlist changes first, then trades.

If the LLM call fails or its output cannot be parsed against the schema, no actions are executed, the user message is still stored, and the endpoint returns 502 `llm_error`.

### System Prompt Guidance

The LLM should be prompted as "FinAlly, an AI trading assistant" with instructions to:
- Analyze portfolio composition, risk concentration, and P&L
- Suggest trades with reasoning
- Execute trades when the user asks or agrees
- Manage the watchlist proactively
- Be concise and data-driven in responses
- Always respond with valid structured JSON

### LLM Mock Mode

When `LLM_MOCK=true`, the backend returns deterministic mock responses instead of calling OpenRouter. This enables:
- Fast, free, reproducible E2E tests
- Development without an API key
- CI/CD pipelines

Mock responses are chosen by simple, case-insensitive pattern matching on the user's message (first match wins), then run through the **same** execution path as real LLM output:

| User message matches | Mock structured output |
|---|---|
| `buy <qty> <TICKER>` (e.g. "buy 5 AAPL") | `message: "Buying <qty> <TICKER>."`, one buy trade |
| `sell <qty> <TICKER>` | `message: "Selling <qty> <TICKER>."`, one sell trade |
| `watch <TICKER>` / `add <TICKER>` | `message: "Added <TICKER> to your watchlist."`, one `add` change |
| `unwatch <TICKER>` / `remove <TICKER>` | `message: "Removed <TICKER> from your watchlist."`, one `remove` change |
| anything else | `message: "Mock response: I received your message."`, no actions |

---

## 10. Frontend Design

### Layout

The frontend is a single-page application with a dense, terminal-inspired layout. The specific component architecture and layout system is up to the Frontend Engineer, but the UI should include these elements:

- **Watchlist panel** — grid/table of watched tickers with: ticker symbol, current price (flashing green/red on change), daily change % (the SSE `session_change_percent` field), and a sparkline mini-chart (accumulated from SSE since page load)
- **Main chart area** — larger chart for the currently selected ticker, with at minimum price over time. Clicking a ticker in the watchlist selects it here.
- **Portfolio heatmap** — treemap visualization where each rectangle is a position, sized by portfolio weight, colored by unrealized P&L **percent** (green = profit, red = loss; intensity scales with magnitude, saturating at ±10%)
- **P&L chart** — line chart showing total portfolio value over time, using data from `portfolio_snapshots`
- **Positions table** — tabular view of all positions: ticker, quantity, avg cost, current price, unrealized P&L, % change
- **Trade bar** — simple input area: ticker field, quantity field, buy button, sell button. Market orders, instant fill.
- **AI chat panel** — docked/collapsible sidebar. Message input, scrolling conversation history, loading indicator while waiting for LLM response. Trade executions and watchlist changes shown inline as confirmations.
- **Header** — portfolio total value (updating live), connection status indicator, cash balance. Live total value is computed on the frontend as `cash_balance + Σ(quantity × latest SSE price)`, using positions from `GET /api/portfolio` (re-fetched after every trade, chat response with actions, and on load). Positions-table current price and unrealized P&L update the same way

### Technical Notes

- Use `EventSource` for SSE connection to `/api/stream/prices`
- Connection status: green when `EventSource.readyState === OPEN` and a message (data or `: ping`) arrived within the last 30s; yellow while `CONNECTING`; red when `CLOSED` or silent for >30s. Note `: ping` comments don't fire `onmessage` — track liveness from data events plus `readyState`, and allow the 30s window in Massive mode
- Canvas-based charting library preferred (Lightweight Charts or Recharts) for performance
- Price flash effect: on receiving a new price, briefly apply a CSS class with background color transition, then remove it
- All API calls go to the same origin (`/api/*`) — no CORS configuration needed
- Tailwind CSS for styling with a custom dark theme

---

## 11. Docker & Deployment

### Multi-Stage Dockerfile

```
Stage 1: Node 20 slim
  - Copy frontend/
  - npm install && npm run build (produces static export)

Stage 2: Python 3.12 slim
  - Install uv
  - Copy backend/
  - uv sync (install Python dependencies from lockfile)
  - Copy frontend build output into a static/ directory
  - Expose port 8000
  - CMD: uvicorn serving FastAPI app
```

FastAPI serves the static frontend files and all API routes on port 8000. All `/api` routers must be registered **before** the static files mount at `/` (`StaticFiles(directory="static", html=True)`), otherwise the catch-all mount swallows API requests.

The backend is copied to `/app` and the volume is mounted at `/app/db`; this is why schema code lives in `backend/app/db/` and never in `backend/db/`.

### Docker Volume

The SQLite database persists via a named Docker volume:

```bash
docker run -v finally-data:/app/db -p 8000:8000 --env-file .env finally
```

The `db/` directory in the project root maps to `/app/db` in the container. The backend writes `finally.db` to this path.

### Start/Stop Scripts

**`scripts/start_mac.sh`** (macOS/Linux):
- Builds the Docker image if not already built (or if `--build` flag passed)
- Runs the container with the volume mount, port mapping, and `.env` file
- Prints the URL to access the app
- Optionally opens the browser

**`scripts/stop_mac.sh`** (macOS/Linux):
- Stops and removes the running container
- Does NOT remove the volume (data persists)

**`scripts/start_windows.ps1`** / **`scripts/stop_windows.ps1`**: PowerShell equivalents for Windows.

All scripts should be idempotent — safe to run multiple times.

### Optional Cloud Deployment

The container is designed to deploy to AWS App Runner, Render, or any container platform. A Terraform configuration for App Runner may be provided in a `deploy/` directory as a stretch goal, but is not part of the core build.

---

## 12. Testing Strategy

### Unit Tests (within `frontend/` and `backend/`)

**Backend (pytest)**:
- Market data: simulator generates valid prices, GBM math is correct, Massive API response parsing works, both implementations conform to the abstract interface
- Portfolio: trade execution logic, P&L calculations, edge cases (selling more than owned, buying with insufficient cash, selling at a loss)
- LLM: structured output parsing handles all valid schemas, graceful handling of malformed responses, trade validation within chat flow
- API routes: correct status codes, response shapes, error handling

**Frontend (React Testing Library or similar)**:
- Component rendering with mock data
- Price flash animation triggers correctly on price changes
- Watchlist CRUD operations
- Portfolio display calculations
- Chat message rendering and loading state

### E2E Tests (in `test/`)

**Infrastructure**: A separate `docker-compose.test.yml` in `test/` that spins up the app container plus a Playwright container. This keeps browser dependencies out of the production image.

**Environment**: Tests run with `LLM_MOCK=true` by default for speed and determinism.

**Key Scenarios**:
- Fresh start: default watchlist appears, $10k balance shown, prices are streaming
- Add and remove a ticker from the watchlist
- Buy shares: cash decreases, position appears, portfolio updates
- Sell shares: cash increases, position updates or disappears
- Portfolio visualization: heatmap renders with correct colors, P&L chart has data points
- AI chat (mocked): send a message, receive a response, trade execution appears inline
- SSE resilience: disconnect and verify reconnection
