"""
Application configuration and settings.

All paths are resolved relative to the project root so the app works
regardless of the current working directory.
"""

import json
import os
from pathlib import Path
from typing import List

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------
# backend/config/settings.py  ->  ../../ = project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIST_DIR = PROJECT_ROOT / "frontend" / "dist"

LEADS_CSV_PATH = DATA_DIR / "leads.csv"
APP_CONFIG_PATH = DATA_DIR / "app_config.json"

# ---------------------------------------------------------------------------
# Network
# ---------------------------------------------------------------------------
BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8765

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
KEYRING_SERVICE = "ai-lead-generator"
KEYRING_USERNAME = "gemini_api_key"

# ---------------------------------------------------------------------------
# Gemini models (Google AI Studio)
# Updated: November 2026 - Older models deprecated, using 3.5 series
# ---------------------------------------------------------------------------
AVAILABLE_GEMINI_MODELS: List[str] = [
    "gemini-3.5-flash",           # Latest fast model
    "gemini-3.5-flash-lite",      # Latest lightweight model
    # Note: Older models (2.5, 2.0, 1.5 series) are no longer available
    # gemini-3.5-pro is not available in the API yet
]

DEFAULT_GEMINI_MODEL = "gemini-3.5-flash"

# ---------------------------------------------------------------------------
# Lead generation pipeline defaults
# ---------------------------------------------------------------------------
DEFAULT_LEAD_LIMIT = 25
MAX_LEAD_LIMIT = 200
MIN_LEAD_LIMIT = 1

# Discovery
DEFAULT_SEARCH_RESULTS = 50
MAX_SEARCH_RESULTS = 200
REQUEST_DELAY_SECONDS = 2.0  # delay between scraping requests

# Scraping
SCRAPER_TIMEOUT_SECONDS = 60
SCRAPER_MAX_RETRIES = 2

# CSV columns (order matters for header)
CSV_COLUMNS = [
    "lead_id",
    "company_name",
    "owner_name",
    "website",
    "email",
    "phone",
    "city",
    "country",
    "business_type",
    "description",
    "source_url",
    "search_query",
    "generated_at",
]


class AppConfig:
    """
    Non-secret application configuration persisted to data/app_config.json.
    Secrets (API keys) are stored separately via secure storage.
    """

    _instance: "AppConfig | None" = None

    def __init__(self) -> None:
        self.gemini_model: str = DEFAULT_GEMINI_MODEL
        self._load()

    # -- singleton helper ---------------------------------------------------
    @classmethod
    def get(cls) -> "AppConfig":
        if cls._instance is None:
            cls._instance = AppConfig()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    # -- persistence --------------------------------------------------------
    def _load(self) -> None:
        ensure_dirs()
        if APP_CONFIG_PATH.exists():
            try:
                data = json.loads(APP_CONFIG_PATH.read_text(encoding="utf-8"))
                model = data.get("gemini_model")
                if isinstance(model, str) and model in AVAILABLE_GEMINI_MODELS:
                    self.gemini_model = model
            except (json.JSONDecodeError, OSError):
                pass  # fall back to defaults

    def save(self) -> None:
        ensure_dirs()
        payload = {"gemini_model": self.gemini_model}
        # atomic write
        tmp = APP_CONFIG_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(APP_CONFIG_PATH)

    # -- getters / setters -------------------------------------------------
    def set_gemini_model(self, model: str) -> None:
        if model not in AVAILABLE_GEMINI_MODELS:
            raise ValueError(f"Unsupported model: {model}")
        self.gemini_model = model
        self.save()


def ensure_dirs() -> None:
    """Create required directories if they don't exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
