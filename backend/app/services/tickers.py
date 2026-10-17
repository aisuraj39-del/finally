"""Ticker symbol validation."""

from __future__ import annotations

import re

from app.errors import ApiError

TICKER_PATTERN = re.compile(r"^[A-Z][A-Z0-9.]{0,9}$")


def normalize_ticker(raw: object) -> str:
    """Uppercase and validate a ticker symbol, raising `invalid_ticker` if malformed."""
    if not isinstance(raw, str):
        raise ApiError("invalid_ticker", "Ticker must be a string")
    ticker = raw.strip().upper()
    if not TICKER_PATTERN.match(ticker):
        raise ApiError("invalid_ticker", f"'{raw}' is not a valid ticker symbol")
    return ticker
