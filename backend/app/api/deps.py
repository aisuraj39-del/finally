"""FastAPI dependencies."""

from __future__ import annotations

from fastapi import Request

from app.services import AppContext


def get_ctx(request: Request) -> AppContext:
    return request.app.state.ctx
