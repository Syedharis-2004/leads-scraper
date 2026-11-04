"""FastAPI dependencies shared across routes."""

from config.settings import AppConfig


def get_app_config() -> AppConfig:
    return AppConfig.get()
