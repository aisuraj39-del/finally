# Backend — Developer Guide

## Project Setup

```bash
cd backend
uv sync --extra dev   # Install all dependencies including test/lint tools
```

## App Layout

```bash
uv run uvicorn app.main:app --reload   # http://localhost:8000 (reads ../.env)
```

- `app/main.py` — `create_app(settings, source_factory)`; lifespan initializes the DB, starts market data with watchlist ∪ positions, runs the 30s snapshot task. Static frontend is mounted at `/` only if `STATIC_DIR` (default `backend/static`) exists
- `app/config.py` — `Settings` from env (`DB_PATH`, `STATIC_DIR`, `MASSIVE_API_KEY`, `LLM_MOCK`)
- `app/db/` — `schema.sql`, `Database` (per-call connections, `BEGIN IMMEDIATE`, lazy init + seed), `utc_now()` fixed-width ISO timestamps
- `app/errors.py` — `ApiError(code, message, status)` → `{"detail": {"code", "message"}}`
- `app/services/` — business logic. **Use `actions.trade / add_to_watchlist / remove_from_watchlist` for any user-initiated change (including LLM chat)**: they validate, run in one transaction, and keep the data source's tracked tickers in sync
- `app/api/` — thin routers over services; get the `AppContext` via `Depends(get_ctx)`

Tests for this layer are in `tests/core/` and use a `FakeSource` with fixed prices (see `tests/core/conftest.py`).

## Market Data API

The market data subsystem lives in `app/market/`. Use these imports:

```python
from app.market import PriceCache, PriceUpdate, MarketDataSource, create_market_data_source
```

### Core Types

- **`PriceUpdate`** — Immutable dataclass: `ticker`, `price`, `previous_price`, `timestamp`, `session_open` (first price seen this session), plus properties `change`, `change_percent` (tick-to-tick), `session_change_percent` (vs session open — the "daily change %"), `direction` ("up"/"down"/"flat"), and `to_dict()` for JSON serialization.

- **`PriceCache`** — Thread-safe in-memory store. Key methods:
  - `update(ticker, price, timestamp=None) -> PriceUpdate`
  - `get(ticker) -> PriceUpdate | None`
  - `get_price(ticker) -> float | None`
  - `get_all() -> dict[str, PriceUpdate]`
  - `remove(ticker)`
  - `version` property — monotonic counter, increments on every update (for SSE change detection)

- **`MarketDataSource`** — Abstract interface implemented by `SimulatorDataSource` and `MassiveDataSource`. Lifecycle: `start(tickers)` -> `add_ticker()` / `remove_ticker()` -> `stop()`.

- **`create_market_data_source(cache)`** — Factory. Returns `MassiveDataSource` if `MASSIVE_API_KEY` is set, otherwise `SimulatorDataSource`.

### SSE Streaming

```python
from app.market import create_stream_router

router = create_stream_router(price_cache)  # Returns a new FastAPI APIRouter per call
# Endpoint: GET /api/stream/prices (text/event-stream)
# Sends one event with all tickers when the cache changes (~500ms), and a
# `: ping` comment after 15s without data. Payload format: see planning/PLAN.md §6.
```

### Seed Data

Default tickers: AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX. Seed prices and per-ticker volatility/drift params are in `app/market/seed_prices.py`.

## Running Tests

```bash
uv run --extra dev pytest -v              # All tests
uv run --extra dev pytest --cov=app       # With coverage
uv run --extra dev ruff check app/ tests/ # Lint
```

## Demo

```bash
uv run market_data_demo.py   # Live terminal dashboard with simulated prices
```
