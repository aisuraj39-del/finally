"""Structured output schema the LLM must return."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TradeInstruction(BaseModel):
    ticker: str = Field(description="Ticker symbol, e.g. AAPL")
    side: Literal["buy", "sell"]
    quantity: float = Field(description="Number of shares; fractional allowed")


class WatchlistInstruction(BaseModel):
    ticker: str = Field(description="Ticker symbol, e.g. PYPL")
    action: Literal["add", "remove"]


# The docstring below is sent to the model as the schema description.
# The lists are required (strict structured outputs need every field present).
class LLMResponse(BaseModel):
    """The assistant's reply to one chat message, plus any actions to execute."""

    message: str = Field(description="Conversational reply shown to the user")
    trades: list[TradeInstruction] = Field(description="Trades to execute now; empty if none")
    watchlist_changes: list[WatchlistInstruction] = Field(
        description="Watchlist changes to make now; empty if none"
    )
