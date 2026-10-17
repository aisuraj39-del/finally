"""Watchlist persistence."""

from __future__ import annotations

import sqlite3

from app.config import DEFAULT_USER_ID
from app.db import new_id, utc_now
from app.errors import ApiError
from app.market import PriceCache

from .tickers import normalize_ticker


def get_watchlist_tickers(conn: sqlite3.Connection, user_id: str = DEFAULT_USER_ID) -> list[str]:
    rows = conn.execute(
        "SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY added_at, ticker", (user_id,)
    ).fetchall()
    return [row["ticker"] for row in rows]


def _entry(ticker: str, added_at: str, cache: PriceCache) -> dict:
    update = cache.get(ticker)
    return {
        "ticker": ticker,
        "price": update.price if update else None,
        "previous_price": update.previous_price if update else None,
        "session_open": update.session_open if update else None,
        "session_change_percent": update.session_change_percent if update else None,
        "direction": update.direction if update else None,
        "added_at": added_at,
    }


def list_watchlist(
    conn: sqlite3.Connection, cache: PriceCache, user_id: str = DEFAULT_USER_ID
) -> list[dict]:
    rows = conn.execute(
        "SELECT ticker, added_at FROM watchlist WHERE user_id = ? ORDER BY added_at, ticker",
        (user_id,),
    ).fetchall()
    return [_entry(row["ticker"], row["added_at"], cache) for row in rows]


def get_entry(
    conn: sqlite3.Connection, cache: PriceCache, ticker: str, user_id: str = DEFAULT_USER_ID
) -> dict:
    row = conn.execute(
        "SELECT ticker, added_at FROM watchlist WHERE user_id = ? AND ticker = ?",
        (user_id, ticker),
    ).fetchone()
    return _entry(row["ticker"], row["added_at"], cache)


def add_ticker(conn: sqlite3.Connection, raw_ticker: object, user_id: str = DEFAULT_USER_ID) -> str:
    """Insert a ticker. Returns the normalized symbol; raises `already_watching`."""
    ticker = normalize_ticker(raw_ticker)
    cur = conn.execute(
        "INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
        (new_id(), user_id, ticker, utc_now()),
    )
    if cur.rowcount == 0:
        raise ApiError("already_watching", f"{ticker} is already on your watchlist", 409)
    return ticker


def remove_ticker(conn: sqlite3.Connection, raw_ticker: object, user_id: str = DEFAULT_USER_ID) -> str:
    """Delete a ticker. Returns the normalized symbol; raises `not_watching`."""
    ticker = normalize_ticker(raw_ticker)
    cur = conn.execute("DELETE FROM watchlist WHERE user_id = ? AND ticker = ?", (user_id, ticker))
    if cur.rowcount == 0:
        raise ApiError("not_watching", f"{ticker} is not on your watchlist", 404)
    return ticker
