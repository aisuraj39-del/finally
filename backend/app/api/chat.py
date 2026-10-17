"""Chat endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, StringConstraints

from app.services import AppContext
from app.services import chat as chat_service

from .deps import get_ctx

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]


@router.post("")
async def post_chat(body: ChatRequest, ctx: AppContext = Depends(get_ctx)) -> dict:
    reply = await chat_service.handle_message(ctx, body.message)
    return {
        "id": reply["id"],
        "message": reply["content"],
        "actions": reply["actions"],
        "created_at": reply["created_at"],
    }


@router.get("/history")
async def get_chat_history(
    limit: int = Query(50, ge=1, le=500), ctx: AppContext = Depends(get_ctx)
) -> dict:
    with ctx.db.connect() as conn:
        return {"messages": chat_service.get_history(conn, limit)}
