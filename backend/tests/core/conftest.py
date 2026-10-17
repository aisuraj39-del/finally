"""Fixtures for backend core tests: a fake market data source and a test client."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.db import Database
from app.main import create_app
from app.market import MarketDataSource, PriceCache


class FakeSource(MarketDataSource):
    """Deterministic data source: prices come from a dict the test controls.

    Tickers missing from `prices` get no price, which simulates Massive mode
    for a symbol that hasn't been polled yet.
    """

    def __init__(self, cache: PriceCache, prices: dict[str, float]) -> None:
        self.cache = cache
        self.prices = prices
        self.tickers: list[str] = []

    async def start(self, tickers: list[str]) -> None:
        for ticker in tickers:
            await self.add_ticker(ticker)

    async def stop(self) -> None:
        pass

    async def add_ticker(self, ticker: str) -> None:
        if ticker not in self.tickers:
            self.tickers.append(ticker)
        if ticker in self.prices:
            self.cache.update(ticker, self.prices[ticker])

    async def remove_ticker(self, ticker: str) -> None:
        if ticker in self.tickers:
            self.tickers.remove(ticker)
        self.cache.remove(ticker)

    def get_tickers(self) -> list[str]:
        return list(self.tickers)

    def set_price(self, ticker: str, price: float) -> None:
        self.prices[ticker] = price
        if ticker in self.tickers:
            self.cache.update(ticker, price)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        db_path=tmp_path / "test.db",
        static_dir=tmp_path / "no-static",
        massive_api_key="",
        llm_mock=True,
        snapshot_interval=3600,
    )


@pytest.fixture
def prices() -> dict[str, float]:
    return {
        "AAPL": 100.0, "GOOGL": 150.0, "MSFT": 400.0, "AMZN": 180.0, "TSLA": 250.0,
        "NVDA": 800.0, "META": 500.0, "JPM": 200.0, "V": 280.0, "NFLX": 600.0,
        "PYPL": 60.0,
    }


@pytest.fixture
def source_holder() -> dict:
    return {}


@pytest.fixture
def client(settings: Settings, prices: dict, source_holder: dict) -> Iterator[TestClient]:
    def factory(cache: PriceCache) -> FakeSource:
        source_holder["source"] = FakeSource(cache, prices)
        return source_holder["source"]

    app = create_app(settings=settings, source_factory=factory)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def source(client: TestClient, source_holder: dict) -> FakeSource:
    return source_holder["source"]


@pytest.fixture
def db(settings: Settings) -> Database:
    database = Database(settings.db_path)
    database.initialize()
    return database
