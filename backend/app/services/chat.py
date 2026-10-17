"""Chat flow: build context, call the LLM (or mock), execute actions, persist.

See PLAN.md §9. Watchlist changes run before trades, each through the same
shared actions as the REST API, so validation is identical to manual trades.
"""

from __future__ import annotations

import json
import logging
import sqlite3

from app.config import DEFAULT_USER_ID
from app.db import new_id, utc_now
from app.errors import ApiError
from app.llm import LLMError, LLMResponse, mock_response
from app.llm import client as llm_client
from app.llm.prompt import SYSTEM_PROMPT, portfolio_context, summarize_actions

from . import actions, portfolio, watchlist
from .actions import AppContext

logger = logging.getLogger(__name__)

HISTORY_LIMIT = 20  # Prior messages sent to the LLM (10 exchanges)


def _row_to_message(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "role": row["role"],
        "content": row["content"],
        "actions": json.loads(row["actions"]) if row["actions"] else None,
        "created_at": row["created_at"],
    }


def get_history(
    conn: sqlite3.Connection, limit: int, user_id: str = DEFAULT_USER_ID
) -> list[dict]:
    """The most recent `limit` messages, oldest first."""
    rows = conn.execute(
        "SELECT * FROM (SELECT rowid AS seq, id, role, content, actions, created_at "
        "FROM chat_messages WHERE user_id = ? ORDER BY created_at DESC, seq DESC LIMIT ?) "
        "ORDER BY created_at, seq",
        (user_id, limit),
    ).fetchall()
    return [_row_to_message(row) for row in rows]


def _store_message(
    conn: sqlite3.Connection,
    role: str,
    content: str,
    actions_json: dict | None = None,
    user_id: str = DEFAULT_USER_ID,
) -> dict:
    message = {
        "id": new_id(),
        "role": role,
        "content": content,
        "actions": actions_json,
        "created_at": utc_now(),
    }
    conn.execute(
        "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            message["id"],
            user_id,
            role,
            content,
            json.dumps(actions_json) if actions_json is not None else None,
            message["created_at"],
        ),
    )
    return message


def build_messages(ctx: AppContext, history: list[dict], user_message: str) -> list[dict]:
    with ctx.db.connect() as conn:
        context = portfolio_context(
            portfolio.get_portfolio(conn, ctx.cache),
            watchlist.list_watchlist(conn, ctx.cache),
        )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": context},
    ]
    for m in history:
        content = m["content"]
        if m["role"] == "assistant":
            content += summarize_actions(m["actions"])
        messages.append({"role": m["role"], "content": content})
    messages.append({"role": "user", "content": user_message})
    return messages


async def _execute(ctx: AppContext, response: LLMResponse) -> dict:
    """Run watchlist changes, then trades. Never raises: failures are recorded."""
    results: dict = {"trades": [], "watchlist_changes": []}

    for change in response.watchlist_changes:
        entry = {"ticker": change.ticker.upper(), "action": change.action}
        try:
            if change.action == "add":
                await actions.add_to_watchlist(ctx, change.ticker)
            else:
                await actions.remove_from_watchlist(ctx, change.ticker)
            entry.update(status="executed", error=None)
        except ApiError as exc:
            entry.update(status="failed", error=exc.code)
        except Exception:
            logger.exception("Watchlist change failed: %s", change)
            entry.update(status="failed", error="internal_error")
        results["watchlist_changes"].append(entry)

    for t in response.trades:
        entry = {"ticker": t.ticker.upper(), "side": t.side, "quantity": t.quantity}
        try:
            trade = await actions.trade(ctx, t.ticker, t.side, t.quantity)
            entry.update(
                ticker=trade["ticker"], quantity=trade["quantity"], status="executed",
                price=trade["price"], error=None,
            )
        except ApiError as exc:
            entry.update(status="failed", price=None, error=exc.code)
        except Exception:
            logger.exception("Trade failed: %s", t)
            entry.update(status="failed", price=None, error="internal_error")
        results["trades"].append(entry)

    return results


_ERROR_TEXT = {
    "insufficient_cash": "insufficient cash",
    "insufficient_shares": "not enough shares",
    "no_price": "no price available",
    "invalid_ticker": "invalid ticker",
    "invalid_quantity": "invalid quantity",
    "already_watching": "already on watchlist",
    "not_watching": "not on watchlist",
}


def _failure_notes(results: dict) -> str:
    notes = []
    for w in results["watchlist_changes"]:
        if w["status"] == "failed":
            reason = _ERROR_TEXT.get(w["error"], w["error"])
            notes.append(f"⚠ Watchlist {w['action']} {w['ticker']} failed: {reason}")
    for t in results["trades"]:
        if t["status"] == "failed":
            reason = _ERROR_TEXT.get(t["error"], t["error"])
            side = t["side"].capitalize()
            notes.append(f"⚠ {side} {t['quantity']:g} {t['ticker']} failed: {reason}")
    return "\n".join(notes)


async def handle_message(ctx: AppContext, user_message: str) -> dict:
    """Process one user chat message end to end. Returns the stored assistant message."""
    with ctx.db.connect() as conn:
        history = get_history(conn, HISTORY_LIMIT)
        _store_message(conn, "user", user_message)

    if ctx.settings.llm_mock:
        response = mock_response(user_message)
    else:
        try:
            response = await llm_client.call_llm(build_messages(ctx, history, user_message))
        except LLMError as exc:
            raise ApiError("llm_error", "The assistant is unavailable right now", 502) from exc

    results = await _execute(ctx, response)

    content = response.message
    if notes := _failure_notes(results):
        content = f"{content}\n\n{notes}" if content else notes

    with ctx.db.connect() as conn:
        return _store_message(conn, "assistant", content, results)
