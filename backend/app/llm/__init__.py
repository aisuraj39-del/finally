"""LLM integration: schema, prompt, real client, and mock."""

from .client import LLMError, call_llm
from .mock import mock_response
from .schema import LLMResponse, TradeInstruction, WatchlistInstruction

__all__ = [
    "LLMError",
    "LLMResponse",
    "TradeInstruction",
    "WatchlistInstruction",
    "call_llm",
    "mock_response",
]
