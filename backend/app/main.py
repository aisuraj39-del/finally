"""FastAPI application entry point.

Run locally:  uv run uvicorn app.main:app --reload
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import routers
from app.config import Settings, get_settings, load_env
from app.db import Database
from app.errors import ApiError, api_error_handler
from app.market import MarketDataSource, PriceCache, create_market_data_source, create_stream_router
from app.services import AppContext, tracked_tickers
from app.services.snapshots import run_snapshot_loop

logger = logging.getLogger(__name__)

SourceFactory = Callable[[PriceCache], MarketDataSource]


def create_app(
    settings: Settings | None = None,
    source_factory: SourceFactory = create_market_data_source,
) -> FastAPI:
    """Build the app. Tests pass their own settings and a fake data source."""
    if settings is None:
        load_env()
        settings = get_settings()

    cache = PriceCache()
    ctx = AppContext(
        settings=settings,
        db=Database(settings.db_path),
        cache=cache,
        source=source_factory(cache),
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        ctx.db.initialize()
        await ctx.source.start(tracked_tickers(ctx))
        snapshot_task = asyncio.create_task(run_snapshot_loop(ctx), name="portfolio-snapshots")
        logger.info("FinAlly started (market data: %s)", settings.market_data_mode)
        try:
            yield
        finally:
            snapshot_task.cancel()
            try:
                await snapshot_task
            except asyncio.CancelledError:
                pass
            await ctx.source.stop()

    app = FastAPI(title="FinAlly", lifespan=lifespan)
    app.state.ctx = ctx
    app.add_exception_handler(ApiError, api_error_handler)

    app.include_router(create_stream_router(cache))
    for router in routers:
        app.include_router(router)

    # Must be mounted after the /api routers, or the catch-all swallows them
    if settings.static_dir.is_dir():
        app.mount("/", StaticFiles(directory=settings.static_dir, html=True), name="static")
    else:
        logger.info("No frontend build at %s; serving API only", settings.static_dir)

    return app


app = create_app()
