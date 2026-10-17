"""System prompt and portfolio context for the chat assistant."""

from __future__ import annotations

import json

SYSTEM_PROMPT = """You are FinAlly, an AI trading assistant inside a simulated trading workstation. \
The user trades a virtual portfolio with fake money; prices are live.

You can:
- Analyze portfolio composition, risk concentration, and P&L
- Suggest trades with brief reasoning
- Execute trades when the user asks or agrees, by listing them in `trades`
- Manage the watchlist proactively, by listing changes in `watchlist_changes`

Rules:
- Trades are market orders filled instantly at the current price. Buys need enough cash; \
sells need enough shares. Quantities may be fractional.
- Only include a trade when the user has asked for it or agreed to it. Never invent trades.
- Use the portfolio context below as the source of truth for prices, cash, and holdings.
- Be concise and data-driven. Use numbers from the context.
- Your actions are executed after you reply, so describe them as being placed \
(e.g. "Buying 10 AAPL"), not as already confirmed. Failures are reported to the user automatically.
- Always respond with JSON matching the schema. Use empty arrays when there is nothing to do."""


def _r(value: float | None, digits: int = 2) -> float | None:
    return round(value, digits) if value is not None else None


def portfolio_context(portfolio: dict, watchlist: list[dict]) -> str:
    """Compact JSON snapshot of the user's account for the model."""
    context = {
        "cash_balance": _r(portfolio["cash_balance"]),
        "total_value": _r(portfolio["total_value"]),
        "unrealized_pnl": _r(portfolio["unrealized_pnl"]),
        "unrealized_pnl_percent": _r(portfolio["unrealized_pnl_percent"]),
        "positions": [
            {
                "ticker": p["ticker"],
                "quantity": p["quantity"],
                "avg_cost": _r(p["avg_cost"]),
                "current_price": _r(p["current_price"]),
                "market_value": _r(p["market_value"]),
                "unrealized_pnl": _r(p["unrealized_pnl"]),
                "unrealized_pnl_percent": _r(p["unrealized_pnl_percent"]),
                "weight_percent": _r(p["weight"] * 100, 1),
            }
            for p in portfolio["positions"]
        ],
        "watchlist": [
            {
                "ticker": w["ticker"],
                "price": _r(w["price"]),
                "change_percent_today": _r(w["session_change_percent"]),
            }
            for w in watchlist
        ],
    }
    return "Current portfolio context:\n" + json.dumps(context)


def summarize_actions(actions: dict | None) -> str:
    """One-line summary of what an earlier assistant turn executed, for history."""
    if not actions:
        return ""
    parts = []
    for t in actions.get("trades", []):
        outcome = f"at ${t['price']:.2f}" if t["status"] == "executed" else f"FAILED ({t['error']})"
        parts.append(f"{t['side']} {t['quantity']:g} {t['ticker']} {outcome}")
    for w in actions.get("watchlist_changes", []):
        outcome = "done" if w["status"] == "executed" else f"FAILED ({w['error']})"
        parts.append(f"watchlist {w['action']} {w['ticker']} {outcome}")
    return f"\n[Actions: {'; '.join(parts)}]" if parts else ""
