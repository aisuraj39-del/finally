"""SQLite connection management, lazy schema creation, and seed data."""

from __future__ import annotations

import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from app.config import DEFAULT_USER_ID

SCHEMA_PATH = Path(__file__).with_name("schema.sql")

DEFAULT_CASH = 10000.0
DEFAULT_WATCHLIST = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"]


def utc_now() -> str:
    """Current UTC time as an ISO 8601 string, e.g. 2026-10-17T14:03:22.123456Z.

    Fixed width, so string comparison orders timestamps correctly.
    """
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def to_utc_iso(value: datetime) -> str:
    """Format any datetime in the same fixed-width form as utc_now()."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def new_id() -> str:
    return str(uuid.uuid4())


class Database:
    """Thin wrapper around a SQLite file.

    A new connection is opened per unit of work. The app runs a single
    process, and SQLite connections are cheap, so this keeps things simple
    and thread-safe.
    """

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """Open a connection; commits on success, rolls back on error."""
        conn = sqlite3.connect(self.path, isolation_level=None)  # Explicit transactions
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        """Create the schema if missing and seed default data on first run."""
        self.path.parent.mkdir(parents=True, exist_ok=True)

        # executescript manages its own transaction, so use a plain connection
        conn = sqlite3.connect(self.path)
        try:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        finally:
            conn.close()

        with self.connect() as conn:
            exists = conn.execute(
                "SELECT 1 FROM users_profile WHERE id = ?", (DEFAULT_USER_ID,)
            ).fetchone()
            if exists:
                return

            now = utc_now()
            conn.execute(
                "INSERT INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)",
                (DEFAULT_USER_ID, DEFAULT_CASH, now),
            )
            conn.executemany(
                "INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
                [(new_id(), DEFAULT_USER_ID, ticker, now) for ticker in DEFAULT_WATCHLIST],
            )
