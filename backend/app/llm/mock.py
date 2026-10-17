"""Deterministic mock LLM for LLM_MOCK=true (E2E tests, development without a key).

Patterns are matched case-insensitively against the user's message; the first
match wins. See PLAN.md §9 "LLM Mock Mode".
"""

from __future__ import annotations

import re

from .schema import LLMResponse, TradeInstruction, WatchlistInstruction

_TICKER = r"([A-Za-z][A-Za-z0-9.]{0,9})"
_QTY = r"(\d+(?:\.\d+)?)"

BUY = re.compile(rf"\bbuy\s+{_QTY}\s+{_TICKER}\b", re.IGNORECASE)
SELL = re.compile(rf"\bsell\s+{_QTY}\s+{_TICKER}\b", re.IGNORECASE)
WATCH = re.compile(rf"\b(?:watch|add)\s+{_TICKER}\b", re.IGNORECASE)
UNWATCH = re.compile(rf"\b(?:unwatch|remove)\s+{_TICKER}\b", re.IGNORECASE)


def _fmt_qty(raw: str) -> str:
    return f"{float(raw):g}"


def mock_response(user_message: str) -> LLMResponse:
    if m := BUY.search(user_message):
        qty, ticker = m.group(1), m.group(2).upper()
        return LLMResponse(
            message=f"Buying {_fmt_qty(qty)} {ticker}.",
            trades=[TradeInstruction(ticker=ticker, side="buy", quantity=float(qty))],
            watchlist_changes=[],
        )
    if m := SELL.search(user_message):
        qty, ticker = m.group(1), m.group(2).upper()
        return LLMResponse(
            message=f"Selling {_fmt_qty(qty)} {ticker}.",
            trades=[TradeInstruction(ticker=ticker, side="sell", quantity=float(qty))],
            watchlist_changes=[],
        )
    if m := WATCH.search(user_message):
        ticker = m.group(1).upper()
        return LLMResponse(
            message=f"Added {ticker} to your watchlist.",
            trades=[],
            watchlist_changes=[WatchlistInstruction(ticker=ticker, action="add")],
        )
    if m := UNWATCH.search(user_message):
        ticker = m.group(1).upper()
        return LLMResponse(
            message=f"Removed {ticker} from your watchlist.",
            trades=[],
            watchlist_changes=[WatchlistInstruction(ticker=ticker, action="remove")],
        )
    return LLMResponse(
        message="Mock response: I received your message.", trades=[], watchlist_changes=[]
    )
