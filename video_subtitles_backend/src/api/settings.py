from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env if present (non-fatal in prod)
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self) -> None:
        # MEDIA_ROOT configuration - default to ./media if not provided
        media_root_env: Optional[str] = os.getenv("MEDIA_ROOT")
        if media_root_env:
            self.MEDIA_ROOT = Path(media_root_env).expanduser().resolve()
        else:
            self.MEDIA_ROOT = Path("media").resolve()

        # Optional: environment marker (development|production|test)
        self.ENV = os.getenv("ENV", "development").lower()

        # Optional flag to seed database with sample data if empty
        # Use "true"/"1"/"yes" to enable
        self.SEED_DB = os.getenv("SEED_DB", "false").strip().lower() in {"1", "true", "yes"}

        # Database variables (must be provided by environment)
        self.DB_HOST = os.getenv("DB_HOST")
        self.DB_PORT = os.getenv("DB_PORT")
        self.DB_NAME = os.getenv("DB_NAME")
        self.DB_USER = os.getenv("DB_USER")
        self.DB_PASSWORD = os.getenv("DB_PASSWORD")

    def ensure_media_dirs(self) -> None:
        """Ensure the MEDIA_ROOT and subdirectories exist."""
        (self.MEDIA_ROOT).mkdir(parents=True, exist_ok=True)
        (self.MEDIA_ROOT / "videos").mkdir(parents=True, exist_ok=True)
        (self.MEDIA_ROOT / "subtitles").mkdir(parents=True, exist_ok=True)


# Singleton-like access
settings = Settings()
