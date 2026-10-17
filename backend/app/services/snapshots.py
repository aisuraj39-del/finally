"""Background task recording portfolio value snapshots for the P&L chart."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from app.db import to_utc_iso

from . import portfolio
from .actions import AppContext

logger = logging.getLogger(__name__)


def take_snapshot(ctx: AppContext) -> None:
    """Record one snapshot and prune those past the retention window."""
    cutoff = to_utc_iso(datetime.now(UTC) - timedelta(days=ctx.settings.snapshot_retention_days))
    with ctx.db.connect() as conn:
        portfolio.record_snapshot(conn, ctx.cache)
        portfolio.prune_snapshots(conn, cutoff)


async def run_snapshot_loop(ctx: AppContext) -> None:
    """Take a snapshot every `snapshot_interval` seconds until cancelled."""
    while True:
        try:
            take_snapshot(ctx)
        except Exception:
            logger.exception("Portfolio snapshot failed")
        await asyncio.sleep(ctx.settings.snapshot_interval)
