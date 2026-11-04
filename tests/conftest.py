"""
Pytest configuration and fixtures.

Ensures the backend package is importable and uses a temporary
data directory so tests never touch the real CSV or config files.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Add backend to path
BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))


@pytest.fixture(autouse=True)
def temp_data_dir(tmp_path, monkeypatch):
    """
    Redirect all data/log paths to a temporary directory so tests
    never modify the real leads.csv or config files.
    """
    from config import settings as cfg

    tmp_data = tmp_path / "data"
    tmp_logs = tmp_path / "logs"
    tmp_data.mkdir()
    tmp_logs.mkdir()

    monkeypatch.setattr(cfg, "DATA_DIR", tmp_data)
    monkeypatch.setattr(cfg, "LOGS_DIR", tmp_logs)
    monkeypatch.setattr(cfg, "LEADS_CSV_PATH", tmp_data / "leads.csv")
    monkeypatch.setattr(cfg, "APP_CONFIG_PATH", tmp_data / "app_config.json")

    # Also patch the CSV service module's references
    from services import csv_service
    monkeypatch.setattr(csv_service, "LEADS_CSV_PATH", tmp_data / "leads.csv")
    # The lock path is derived from LEADS_CSV_PATH, so it will follow

    yield tmp_data


@pytest.fixture
def app_client():
    """FastAPI TestClient for endpoint tests."""
    from fastapi.testclient import TestClient
    from main import app

    with TestClient(app) as client:
        yield client
