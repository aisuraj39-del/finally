"""Portfolio endpoints: valuation, trading, and value history."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.db import to_utc_iso
from app.errors import ApiError
from app.services import AppContext, actions
from app.services import portfolio as portfolio_service

from .deps import get_ctx

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


class TradeRequest(BaseModel):
    ticker: str
    quantity: float
    side: str


@router.get("")
async def get_portfolio(ctx: AppContext = Depends(get_ctx)) -> dict:
    with ctx.db.connect() as conn:
        return portfolio_service.get_portfolio(conn, ctx.cache)


@router.post("/trade")
async def post_trade(body: TradeRequest, ctx: AppContext = Depends(get_ctx)) -> dict:
    trade = await actions.trade(ctx, body.ticker, body.side, body.quantity)
    with ctx.db.connect() as conn:
        return {"trade": trade, "portfolio": portfolio_service.get_portfolio(conn, ctx.cache)}


@router.get("/history")
async def get_history(since: str | None = None, ctx: AppContext = Depends(get_ctx)) -> dict:
    if since:
        try:
            since_iso = to_utc_iso(datetime.fromisoformat(since))
        except ValueError:
            raise ApiError("invalid_since", f"'{since}' is not an ISO 8601 timestamp") from None
    else:
        since_iso = to_utc_iso(datetime.now(UTC) - timedelta(hours=24))

    with ctx.db.connect() as conn:
        return {"snapshots": portfolio_service.get_history(conn, since_iso)}
