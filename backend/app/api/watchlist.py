"""Watchlist endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from app.services import AppContext, actions
from app.services import watchlist as watchlist_service

from .deps import get_ctx

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


class AddTickerRequest(BaseModel):
    ticker: str


@router.get("")
async def get_watchlist(ctx: AppContext = Depends(get_ctx)) -> dict:
    with ctx.db.connect() as conn:
        return {"tickers": watchlist_service.list_watchlist(conn, ctx.cache)}


@router.post("", status_code=201)
async def post_watchlist(body: AddTickerRequest, ctx: AppContext = Depends(get_ctx)) -> dict:
    return await actions.add_to_watchlist(ctx, body.ticker)


@router.delete("/{ticker}", status_code=204)
async def delete_watchlist(ticker: str, ctx: AppContext = Depends(get_ctx)) -> Response:
    await actions.remove_from_watchlist(ctx, ticker)
    return Response(status_code=204)
