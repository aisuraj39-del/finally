"""Unit tests for trade execution and portfolio valuation."""

import pytest

from app.errors import ApiError
from app.market import PriceCache
from app.services.portfolio import execute_trade, get_portfolio


@pytest.fixture
def cache() -> PriceCache:
    cache = PriceCache()
    cache.update("AAPL", 100.0)
    cache.update("TSLA", 250.0)
    return cache


def trade(db, cache, ticker, side, qty):
    with db.connect() as conn:
        return execute_trade(conn, cache, ticker, side, qty)


def portfolio(db, cache):
    with db.connect() as conn:
        return get_portfolio(conn, cache)


class TestBuy:
    def test_buy_creates_position_and_debits_cash(self, db, cache):
        result = trade(db, cache, "aapl", "buy", 10)

        assert result.opened_position
        assert result.trade["ticker"] == "AAPL"
        assert result.trade["price"] == 100.0
        p = portfolio(db, cache)
        assert p["cash_balance"] == 9000.0
        assert p["positions"][0]["quantity"] == 10
        assert p["positions"][0]["avg_cost"] == 100.0

    def test_buy_more_averages_cost(self, db, cache):
        trade(db, cache, "AAPL", "buy", 10)
        cache.update("AAPL", 120.0)
        result = trade(db, cache, "AAPL", "buy", 10)

        assert not result.opened_position
        pos = portfolio(db, cache)["positions"][0]
        assert pos["quantity"] == 20
        assert pos["avg_cost"] == pytest.approx(110.0)

    def test_insufficient_cash(self, db, cache):
        with pytest.raises(ApiError) as exc:
            trade(db, cache, "AAPL", "buy", 101)
        assert exc.value.code == "insufficient_cash"
        assert portfolio(db, cache)["cash_balance"] == 10000.0

    def test_buy_exactly_all_cash(self, db, cache):
        trade(db, cache, "AAPL", "buy", 100)
        assert portfolio(db, cache)["cash_balance"] == pytest.approx(0.0)

    def test_fractional_quantity_rounded(self, db, cache):
        result = trade(db, cache, "AAPL", "buy", 1.234567)
        assert result.trade["quantity"] == 1.2346


class TestSell:
    def test_partial_sell(self, db, cache):
        trade(db, cache, "AAPL", "buy", 10)
        cache.update("AAPL", 110.0)
        result = trade(db, cache, "AAPL", "sell", 4)

        assert not result.closed_position
        p = portfolio(db, cache)
        assert p["cash_balance"] == pytest.approx(9000 + 440)
        assert p["positions"][0]["quantity"] == 6
        assert p["positions"][0]["avg_cost"] == 100.0  # Unchanged on sells

    def test_full_sell_removes_position(self, db, cache):
        trade(db, cache, "AAPL", "buy", 10)
        result = trade(db, cache, "AAPL", "sell", 10)

        assert result.closed_position
        assert portfolio(db, cache)["positions"] == []

    def test_sell_at_loss(self, db, cache):
        trade(db, cache, "AAPL", "buy", 10)
        cache.update("AAPL", 80.0)
        trade(db, cache, "AAPL", "sell", 10)
        assert portfolio(db, cache)["cash_balance"] == pytest.approx(9800.0)

    def test_sell_more_than_owned(self, db, cache):
        trade(db, cache, "AAPL", "buy", 5)
        with pytest.raises(ApiError) as exc:
            trade(db, cache, "AAPL", "sell", 6)
        assert exc.value.code == "insufficient_shares"

    def test_sell_unowned(self, db, cache):
        with pytest.raises(ApiError) as exc:
            trade(db, cache, "AAPL", "sell", 1)
        assert exc.value.code == "insufficient_shares"

    def test_fractional_dust_closes_position(self, db, cache):
        trade(db, cache, "AAPL", "buy", 0.3)
        trade(db, cache, "AAPL", "buy", 0.3)
        trade(db, cache, "AAPL", "sell", 0.6)
        assert portfolio(db, cache)["positions"] == []


class TestValidation:
    @pytest.mark.parametrize("qty", [0, -1, 0.00001, "5", True])
    def test_invalid_quantity(self, db, cache, qty):
        with pytest.raises(ApiError) as exc:
            trade(db, cache, "AAPL", "buy", qty)
        assert exc.value.code == "invalid_quantity"

    def test_invalid_side(self, db, cache):
        with pytest.raises(ApiError) as exc:
            trade(db, cache, "AAPL", "hold", 1)
        assert exc.value.code == "invalid_side"

    @pytest.mark.parametrize("ticker", ["", "1ABC", "TOOLONGTICKER", "AA PL", "$AAPL"])
    def test_invalid_ticker(self, db, cache, ticker):
        with pytest.raises(ApiError) as exc:
            trade(db, cache, ticker, "buy", 1)
        assert exc.value.code == "invalid_ticker"

    def test_no_price(self, db, cache):
        with pytest.raises(ApiError) as exc:
            trade(db, cache, "ZZZZ", "buy", 1)
        assert exc.value.code == "no_price"


class TestValuation:
    def test_pnl_and_weights(self, db, cache):
        trade(db, cache, "AAPL", "buy", 10)  # 1000
        trade(db, cache, "TSLA", "buy", 4)  # 1000
        cache.update("AAPL", 150.0)  # +500
        cache.update("TSLA", 200.0)  # -200

        p = portfolio(db, cache)
        assert p["cash_balance"] == 8000.0
        assert p["positions_value"] == 2300.0
        assert p["total_value"] == 10300.0
        assert p["unrealized_pnl"] == 300.0
        assert p["unrealized_pnl_percent"] == pytest.approx(15.0)
        by_ticker = {pos["ticker"]: pos for pos in p["positions"]}
        assert by_ticker["AAPL"]["unrealized_pnl_percent"] == pytest.approx(50.0)
        assert by_ticker["TSLA"]["unrealized_pnl"] == -200.0
        assert sum(pos["weight"] for pos in p["positions"]) == pytest.approx(2300 / 10300)

    def test_missing_price_falls_back_to_avg_cost(self, db, cache):
        trade(db, cache, "AAPL", "buy", 10)
        cache.remove("AAPL")
        pos = portfolio(db, cache)["positions"][0]
        assert pos["current_price"] == 100.0
        assert pos["unrealized_pnl"] == 0.0

    def test_trade_records_snapshot_and_log(self, db, cache):
        trade(db, cache, "AAPL", "buy", 10)
        with db.connect() as conn:
            assert conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0] == 1
            snap = conn.execute("SELECT total_value FROM portfolio_snapshots").fetchone()[0]
        assert snap == 10000.0
