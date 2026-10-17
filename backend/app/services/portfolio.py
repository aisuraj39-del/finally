"""Portfolio valuation, trade execution, and snapshots.

Functions here operate on an open SQLite connection so callers control the
transaction boundary. Prices always come from the PriceCache.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from app.config import DEFAULT_USER_ID
from app.db import new_id, utc_now
from app.errors import ApiError
from app.market import PriceCache

from .tickers import normalize_ticker

QUANTITY_DECIMALS = 4
SHARE_EPSILON = 1e-6  # Positions smaller than this are treated as closed
CASH_EPSILON = 1e-9


@dataclass(frozen=True)
class TradeResult:
    trade: dict
    opened_position: bool  # Ticker had no position before this trade
    closed_position: bool  # Position was fully sold


def get_cash(conn: sqlite3.Connection, user_id: str = DEFAULT_USER_ID) -> float:
    row = conn.execute("SELECT cash_balance FROM users_profile WHERE id = ?", (user_id,)).fetchone()
    return float(row["cash_balance"])


def get_position_tickers(conn: sqlite3.Connection, user_id: str = DEFAULT_USER_ID) -> set[str]:
    rows = conn.execute("SELECT ticker FROM positions WHERE user_id = ?", (user_id,)).fetchall()
    return {row["ticker"] for row in rows}


def get_portfolio(
    conn: sqlite3.Connection, cache: PriceCache, user_id: str = DEFAULT_USER_ID
) -> dict:
    """Current cash, positions with live valuation, and totals."""
    cash = get_cash(conn, user_id)
    rows = conn.execute(
        "SELECT ticker, quantity, avg_cost FROM positions WHERE user_id = ? ORDER BY ticker",
        (user_id,),
    ).fetchall()

    positions = []
    for row in rows:
        quantity = float(row["quantity"])
        avg_cost = float(row["avg_cost"])
        price = cache.get_price(row["ticker"])
        current_price = price if price is not None else avg_cost
        market_value = quantity * current_price
        cost_basis = quantity * avg_cost
        pnl = market_value - cost_basis
        positions.append(
            {
                "ticker": row["ticker"],
                "quantity": quantity,
                "avg_cost": avg_cost,
                "current_price": current_price,
                "market_value": market_value,
                "unrealized_pnl": pnl,
                "unrealized_pnl_percent": (pnl / cost_basis * 100) if cost_basis else 0.0,
            }
        )

    positions_value = sum(p["market_value"] for p in positions)
    cost_total = sum(p["quantity"] * p["avg_cost"] for p in positions)
    total_value = cash + positions_value
    unrealized_pnl = positions_value - cost_total

    for p in positions:
        p["weight"] = p["market_value"] / total_value if total_value else 0.0

    return {
        "cash_balance": cash,
        "positions_value": positions_value,
        "total_value": total_value,
        "unrealized_pnl": unrealized_pnl,
        "unrealized_pnl_percent": (unrealized_pnl / cost_total * 100) if cost_total else 0.0,
        "positions": positions,
    }


def _validate_quantity(quantity: object) -> float:
    if isinstance(quantity, bool) or not isinstance(quantity, int | float):
        raise ApiError("invalid_quantity", "Quantity must be a number")
    rounded = round(float(quantity), QUANTITY_DECIMALS)
    if not rounded > 0:
        raise ApiError("invalid_quantity", "Quantity must be greater than 0")
    return rounded


def execute_trade(
    conn: sqlite3.Connection,
    cache: PriceCache,
    ticker: str,
    side: str,
    quantity: object,
    user_id: str = DEFAULT_USER_ID,
) -> TradeResult:
    """Validate and execute a market order at the current cached price.

    Cash, position, trade log, and a portfolio snapshot are all written on
    `conn`; the caller's transaction makes them atomic.
    """
    ticker = normalize_ticker(ticker)
    if side not in ("buy", "sell"):
        raise ApiError("invalid_side", "Side must be 'buy' or 'sell'")
    qty = _validate_quantity(quantity)

    price = cache.get_price(ticker)
    if price is None:
        raise ApiError("no_price", f"No price available for {ticker}")

    cash = get_cash(conn, user_id)
    position = conn.execute(
        "SELECT quantity, avg_cost FROM positions WHERE user_id = ? AND ticker = ?",
        (user_id, ticker),
    ).fetchone()
    held = float(position["quantity"]) if position else 0.0
    now = utc_now()
    opened = closed = False

    if side == "buy":
        cost = qty * price
        if cost > cash + CASH_EPSILON:
            raise ApiError(
                "insufficient_cash", f"Need ${cost:,.2f} to buy {qty:g} {ticker}, have ${cash:,.2f}"
            )
        if position:
            new_qty = held + qty
            new_avg = (held * float(position["avg_cost"]) + cost) / new_qty
            conn.execute(
                "UPDATE positions SET quantity = ?, avg_cost = ?, updated_at = ? "
                "WHERE user_id = ? AND ticker = ?",
                (new_qty, new_avg, now, user_id, ticker),
            )
        else:
            opened = True
            conn.execute(
                "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (new_id(), user_id, ticker, qty, price, now),
            )
        new_cash = cash - cost
    else:
        if qty > held + SHARE_EPSILON:
            raise ApiError(
                "insufficient_shares", f"Cannot sell {qty:g} {ticker}, you hold {held:g}"
            )
        qty = min(qty, held)  # Absorb float dust within the tolerance
        remaining = held - qty
        if remaining < SHARE_EPSILON:
            closed = True
            conn.execute(
                "DELETE FROM positions WHERE user_id = ? AND ticker = ?", (user_id, ticker)
            )
        else:
            conn.execute(
                "UPDATE positions SET quantity = ?, updated_at = ? WHERE user_id = ? AND ticker = ?",
                (remaining, now, user_id, ticker),
            )
        new_cash = cash + qty * price

    conn.execute("UPDATE users_profile SET cash_balance = ? WHERE id = ?", (new_cash, user_id))

    trade = {
        "id": new_id(),
        "ticker": ticker,
        "side": side,
        "quantity": qty,
        "price": price,
        "executed_at": now,
    }
    conn.execute(
        "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (trade["id"], user_id, ticker, side, qty, price, now),
    )
    record_snapshot(conn, cache, user_id)
    return TradeResult(trade=trade, opened_position=opened, closed_position=closed)


def record_snapshot(
    conn: sqlite3.Connection, cache: PriceCache, user_id: str = DEFAULT_USER_ID
) -> float:
    """Store the current total portfolio value. Returns the value recorded."""
    total = get_portfolio(conn, cache, user_id)["total_value"]
    conn.execute(
        "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) VALUES (?, ?, ?, ?)",
        (new_id(), user_id, total, utc_now()),
    )
    return total


def prune_snapshots(
    conn: sqlite3.Connection, before: str, user_id: str = DEFAULT_USER_ID
) -> int:
    """Delete snapshots recorded before the given ISO timestamp."""
    cur = conn.execute(
        "DELETE FROM portfolio_snapshots WHERE user_id = ? AND recorded_at < ?", (user_id, before)
    )
    return cur.rowcount


def get_history(
    conn: sqlite3.Connection, since: str, user_id: str = DEFAULT_USER_ID
) -> list[dict]:
    rows = conn.execute(
        "SELECT total_value, recorded_at FROM portfolio_snapshots "
        "WHERE user_id = ? AND recorded_at >= ? ORDER BY recorded_at",
        (user_id, since),
    ).fetchall()
    return [{"total_value": r["total_value"], "recorded_at": r["recorded_at"]} for r in rows]
