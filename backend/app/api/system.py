"""System endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.services import AppContext

from .deps import get_ctx

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health")
async def health(ctx: AppContext = Depends(get_ctx)) -> dict:
    return {
        "status": "ok",
        "market_data": ctx.settings.market_data_mode,
        "llm_mock": ctx.settings.llm_mock,
    }
