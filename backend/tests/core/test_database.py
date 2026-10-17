"""Tests for lazy schema creation and seeding."""

import pytest

from app.db import DEFAULT_WATCHLIST, Database


class TestInitialize:
    def test_creates_file_and_seeds(self, tmp_path):
        db = Database(tmp_path / "nested" / "finally.db")
        db.initialize()

        assert db.path.exists()
        with db.connect() as conn:
            cash = conn.execute("SELECT cash_balance FROM users_profile").fetchone()[0]
            tickers = [r[0] for r in conn.execute("SELECT ticker FROM watchlist")]
        assert cash == 10000.0
        assert sorted(tickers) == sorted(DEFAULT_WATCHLIST)

    def test_idempotent_and_preserves_data(self, tmp_path):
        db = Database(tmp_path / "finally.db")
        db.initialize()
        with db.connect() as conn:
            conn.execute("UPDATE users_profile SET cash_balance = 42")
            conn.execute("DELETE FROM watchlist WHERE ticker = 'AAPL'")

        db.initialize()

        with db.connect() as conn:
            assert conn.execute("SELECT cash_balance FROM users_profile").fetchone()[0] == 42
            assert conn.execute("SELECT COUNT(*) FROM watchlist").fetchone()[0] == 9

    def test_connect_rolls_back_on_error(self, db):
        with pytest.raises(RuntimeError):
            with db.connect() as conn:
                conn.execute("UPDATE users_profile SET cash_balance = 1")
                raise RuntimeError("boom")

        with db.connect() as conn:
            assert conn.execute("SELECT cash_balance FROM users_profile").fetchone()[0] == 10000.0
