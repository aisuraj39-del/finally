"""API tests: status codes, response shapes, errors, and ticker tracking."""

from datetime import UTC, datetime, timedelta

from app.db import DEFAULT_WATCHLIST


def error_code(response) -> str:
    return response.json()["detail"]["code"]


class TestHealth:
    def test_health(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok", "market_data": "simulator", "llm_mock": True}


class TestPortfolio:
    def test_fresh_portfolio(self, client):
        r = client.get("/api/portfolio")
        assert r.status_code == 200
        body = r.json()
        assert body["cash_balance"] == 10000.0
        assert body["total_value"] == 10000.0
        assert body["positions"] == []

    def test_buy_returns_trade_and_portfolio(self, client):
        r = client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 10, "side": "buy"})
        assert r.status_code == 200
        body = r.json()
        assert body["trade"]["ticker"] == "AAPL"
        assert body["trade"]["price"] == 100.0
        assert body["trade"]["executed_at"].endswith("Z")
        assert body["portfolio"]["cash_balance"] == 9000.0
        position = body["portfolio"]["positions"][0]
        assert set(position) == {
            "ticker", "quantity", "avg_cost", "current_price", "market_value",
            "unrealized_pnl", "unrealized_pnl_percent", "weight",
        }

    def test_trade_error_shape(self, client):
        r = client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1000, "side": "buy"})
        assert r.status_code == 400
        assert error_code(r) == "insufficient_cash"
        assert "message" in r.json()["detail"]

    def test_malformed_body_is_422(self, client):
        r = client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": "lots", "side": "buy"})
        assert r.status_code == 422

    def test_history_includes_trade_snapshot(self, client):
        client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "buy"})
        r = client.get("/api/portfolio/history")
        assert r.status_code == 200
        snapshots = r.json()["snapshots"]
        assert len(snapshots) >= 2  # Startup snapshot + post-trade snapshot
        times = [s["recorded_at"] for s in snapshots]
        assert times == sorted(times)

    def test_history_since_filters(self, client):
        future = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
        r = client.get("/api/portfolio/history", params={"since": future})
        assert r.json()["snapshots"] == []

    def test_history_invalid_since(self, client):
        r = client.get("/api/portfolio/history", params={"since": "yesterday"})
        assert r.status_code == 400
        assert error_code(r) == "invalid_since"


class TestWatchlist:
    def test_default_watchlist_with_prices(self, client):
        r = client.get("/api/watchlist")
        assert r.status_code == 200
        tickers = r.json()["tickers"]
        # Seeded with one timestamp, so ordering falls back to ticker
        assert [t["ticker"] for t in tickers] == sorted(DEFAULT_WATCHLIST)
        aapl = next(t for t in tickers if t["ticker"] == "AAPL")
        assert aapl["price"] == 100.0
        assert aapl["session_open"] == 100.0
        assert aapl["added_at"].endswith("Z")

    def test_add_ticker(self, client, source):
        r = client.post("/api/watchlist", json={"ticker": "pypl"})
        assert r.status_code == 201
        assert r.json()["ticker"] == "PYPL"
        assert r.json()["price"] == 60.0
        assert "PYPL" in source.get_tickers()

    def test_add_unpriced_ticker_has_null_price(self, client):
        r = client.post("/api/watchlist", json={"ticker": "ZZZZ"})
        assert r.status_code == 201
        assert r.json()["price"] is None

    def test_add_duplicate(self, client):
        r = client.post("/api/watchlist", json={"ticker": "AAPL"})
        assert r.status_code == 409
        assert error_code(r) == "already_watching"

    def test_add_invalid(self, client):
        r = client.post("/api/watchlist", json={"ticker": "not a ticker"})
        assert r.status_code == 400
        assert error_code(r) == "invalid_ticker"

    def test_remove_ticker(self, client, source):
        r = client.delete("/api/watchlist/NFLX")
        assert r.status_code == 204
        assert "NFLX" not in source.get_tickers()
        tickers = [t["ticker"] for t in client.get("/api/watchlist").json()["tickers"]]
        assert "NFLX" not in tickers

    def test_remove_missing(self, client):
        r = client.delete("/api/watchlist/PYPL")
        assert r.status_code == 404
        assert error_code(r) == "not_watching"


class TestTickerTracking:
    """Tracked tickers = watchlist ∪ open positions."""

    def test_removing_held_ticker_keeps_price(self, client, source):
        client.post("/api/portfolio/trade", json={"ticker": "NVDA", "quantity": 1, "side": "buy"})
        client.delete("/api/watchlist/NVDA")

        assert "NVDA" in source.get_tickers()
        source.set_price("NVDA", 900.0)
        position = client.get("/api/portfolio").json()["positions"][0]
        assert position["current_price"] == 900.0

    def test_selling_unwatched_position_stops_tracking(self, client, source):
        client.post("/api/portfolio/trade", json={"ticker": "NVDA", "quantity": 1, "side": "buy"})
        client.delete("/api/watchlist/NVDA")
        client.post("/api/portfolio/trade", json={"ticker": "NVDA", "quantity": 1, "side": "sell"})
        assert "NVDA" not in source.get_tickers()

    def test_selling_watched_position_keeps_tracking(self, client, source):
        client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "buy"})
        client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "sell"})
        assert "AAPL" in source.get_tickers()

    def test_buy_unwatched_ticker_starts_tracking(self, client, source):
        r = client.post("/api/portfolio/trade", json={"ticker": "PYPL", "quantity": 2, "side": "buy"})
        assert r.status_code == 200
        assert "PYPL" in source.get_tickers()

    def test_failed_trade_on_unwatched_ticker_does_not_leak(self, client, source):
        r = client.post("/api/portfolio/trade", json={"ticker": "ZZZZ", "quantity": 1, "side": "buy"})
        assert error_code(r) == "no_price"
        assert "ZZZZ" not in source.get_tickers()

    def test_tracking_restored_on_restart(self, settings, prices, source_holder, client):
        client.post("/api/portfolio/trade", json={"ticker": "PYPL", "quantity": 1, "side": "buy"})

        from fastapi.testclient import TestClient

        from app.main import create_app
        from tests.core.conftest import FakeSource

        restarted: dict = {}

        def factory(cache):
            restarted["source"] = FakeSource(cache, prices)
            return restarted["source"]

        with TestClient(create_app(settings=settings, source_factory=factory)):
            assert "PYPL" in restarted["source"].get_tickers()
            assert len(restarted["source"].get_tickers()) == 11
