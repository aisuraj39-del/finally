"""LLM call via LiteLLM -> OpenRouter, with Cerebras as the inference provider."""

from __future__ import annotations

import asyncio
import logging

from litellm import completion
from pydantic import ValidationError

from .schema import LLMResponse

logger = logging.getLogger(__name__)

MODEL = "openrouter/openai/gpt-oss-120b"
EXTRA_BODY = {"provider": {"order": ["cerebras"]}}
TIMEOUT_SECONDS = 30


class LLMError(Exception):
    """The LLM call failed or returned output that doesn't match the schema."""


def _call_sync(messages: list[dict]) -> LLMResponse:
    try:
        response = completion(
            model=MODEL,
            messages=messages,
            response_format=LLMResponse,
            reasoning_effort="low",
            extra_body=EXTRA_BODY,
            timeout=TIMEOUT_SECONDS,
        )
    except Exception as exc:
        logger.exception("LLM call failed")
        raise LLMError(f"LLM call failed: {exc}") from exc

    content = response.choices[0].message.content or ""
    try:
        return LLMResponse.model_validate_json(content)
    except ValidationError as exc:
        logger.warning("LLM returned unparseable output: %.500s", content)
        raise LLMError("LLM returned output that does not match the schema") from exc


async def call_llm(messages: list[dict]) -> LLMResponse:
    """Call the model off the event loop (LiteLLM's `completion` is blocking)."""
    return await asyncio.to_thread(_call_sync, messages)
