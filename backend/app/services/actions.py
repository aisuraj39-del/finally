"""User-facing actions shared by the REST API and the LLM chat flow.

Each action runs its DB work in one transaction, then keeps the market data
source in sync with the tracked set: watchlist ∪ open positions.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings
from app.db import Database
from app.market import MarketDataSource, PriceCache

from . import portfolio, watchlist
from .tickers import normalize_ticker


@dataclass
class AppContext:
    settings: Settings
    db: Database
    cache: PriceCache
    source: MarketDataSource


def tracked_tickers(ctx: AppContext) -> list[str]:
    """Tickers that need live prices: the watchlist plus every held position."""
    with ctx.db.connect() as conn:
        watched = watchlist.get_watchlist_tickers(conn)
        held = portfolio.get_position_tickers(conn)
    return watched + sorted(held - set(watched))


async def sync_ticker(ctx: AppContext, ticker: str) -> None:
    """Start or stop pricing `ticker` depending on whether it is still needed."""
    with ctx.db.connect() as conn:
        needed = ticker in watchlist.get_watchlist_tickers(conn) or ticker in (
            portfolio.get_position_tickers(conn)
        )
    active = ticker in ctx.source.get_tickers()
    if needed and not active:
        await ctx.source.add_ticker(ticker)
    elif not needed and active:
        await ctx.source.remove_ticker(ticker)


async def trade(ctx: AppContext, ticker: object, side: object, quantity: object) -> dict:
    """Execute a market order. Returns the trade record; raises ApiError on failure."""
    symbol = normalize_ticker(ticker)

    # A ticker that isn't tracked has no price yet. Start tracking it so the
    # simulator can price it immediately (Massive will report no_price until
    # its next poll); sync_ticker below stops tracking it again if unneeded.
    if symbol not in ctx.source.get_tickers():
        await ctx.source.add_ticker(symbol)

    try:
        with ctx.db.connect() as conn:
            result = portfolio.execute_trade(conn, ctx.cache, symbol, side, quantity)
    finally:
        await sync_ticker(ctx, symbol)
    return result.trade


async def add_to_watchlist(ctx: AppContext, ticker: object) -> dict:
    """Add a ticker to the watchlist. Returns the watchlist entry."""
    with ctx.db.connect() as conn:
        symbol = watchlist.add_ticker(conn, ticker)
    await sync_ticker(ctx, symbol)
    with ctx.db.connect() as conn:
        return watchlist.get_entry(conn, ctx.cache, symbol)


async def remove_from_watchlist(ctx: AppContext, ticker: object) -> str:
    """Remove a ticker from the watchlist. Prices keep flowing if a position is held."""
    with ctx.db.connect() as conn:
        symbol = watchlist.remove_ticker(conn, ticker)
    await sync_ticker(ctx, symbol)
    return symbol
