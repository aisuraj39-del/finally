"""Tests for the SSE streaming endpoint."""

import json

from fastapi import FastAPI

from app.market.cache import PriceCache
from app.market.stream import _generate_events, create_stream_router


class FakeRequest:
    """Minimal stand-in for a Starlette Request."""

    client = None

    def __init__(self, disconnect_after: int):
        self._checks_left = disconnect_after

    async def is_disconnected(self) -> bool:
        self._checks_left -= 1
        return self._checks_left < 0


async def collect(gen) -> list[str]:
    return [chunk async for chunk in gen]


class TestCreateStreamRouter:
    def test_repeated_calls_do_not_duplicate_routes(self):
        """Each call returns a fresh router with exactly one route."""
        cache = PriceCache()
        r1 = create_stream_router(cache)
        r2 = create_stream_router(cache)
        assert r1 is not r2
        assert len(r1.routes) == 1
        assert len(r2.routes) == 1

    def test_route_path(self):
        app = FastAPI()
        app.include_router(create_stream_router(PriceCache()))
        assert "/api/stream/prices" in [route.path for route in app.routes]


class TestGenerateEvents:
    async def test_sends_retry_then_data(self):
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        cache.update("AAPL", 191.00)

        chunks = await collect(_generate_events(cache, FakeRequest(1), interval=0))

        assert chunks[0] == "retry: 1000\n\n"
        assert chunks[1].startswith("data: ")
        data = json.loads(chunks[1][len("data: "):])
        assert data["AAPL"]["price"] == 191.00
        assert data["AAPL"]["session_open"] == 190.00
        assert "session_change_percent" in data["AAPL"]

    async def test_no_duplicate_data_when_unchanged(self):
        cache = PriceCache()
        cache.update("AAPL", 190.00)

        chunks = await collect(_generate_events(cache, FakeRequest(3), interval=0))

        assert sum(c.startswith("data: ") for c in chunks) == 1

    async def test_keepalive_ping_when_idle(self):
        cache = PriceCache()  # Empty cache: no data events ever

        chunks = await collect(
            _generate_events(cache, FakeRequest(2), interval=0, keepalive_interval=0)
        )

        assert ": ping\n\n" in chunks
        assert not any(c.startswith("data: ") for c in chunks)
