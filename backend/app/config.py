"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# app/config.py -> app/ -> backend/ -> project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(__file__).resolve().parents[1]

DEFAULT_USER_ID = "default"


def load_env() -> None:
    """Load the project-root .env for local development.

    Variables already present in the environment take precedence, so values
    supplied via `docker --env-file` are never overridden.
    """
    load_dotenv(PROJECT_ROOT / ".env", override=False)


@dataclass(frozen=True)
class Settings:
    db_path: Path
    static_dir: Path
    massive_api_key: str
    llm_mock: bool
    snapshot_interval: float = 30.0
    snapshot_retention_days: int = 7

    @property
    def market_data_mode(self) -> str:
        return "massive" if self.massive_api_key else "simulator"


def get_settings() -> Settings:
    """Build settings from the current environment."""
    db_path = os.environ.get("DB_PATH", "").strip()
    static_dir = os.environ.get("STATIC_DIR", "").strip()
    return Settings(
        db_path=Path(db_path) if db_path else PROJECT_ROOT / "db" / "finally.db",
        static_dir=Path(static_dir) if static_dir else BACKEND_DIR / "static",
        massive_api_key=os.environ.get("MASSIVE_API_KEY", "").strip(),
        llm_mock=os.environ.get("LLM_MOCK", "").strip().lower() == "true",
    )
