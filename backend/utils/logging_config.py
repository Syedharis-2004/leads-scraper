"""
Centralised logging configuration.

Logs are written to logs/app.log (rotating) and stdout.
Secrets are automatically redacted via a logging filter.
"""

import logging
import re
from logging.handlers import RotatingFileHandler

from config.settings import LOGS_DIR, ensure_dirs

# ---------------------------------------------------------------------------
# Secret redaction
# ---------------------------------------------------------------------------
# Patterns that look like API keys, tokens, or Gemini keys.
_API_KEY_PATTERN = re.compile(r"(AIza[0-9A-Za-z\-_]{20,})", re.IGNORECASE)
_BEARER_PATTERN = re.compile(r"(Bearer\s+[\w\-\.]+)", re.IGNORECASE)


class RedactingFilter(logging.Filter):
    """Strip sensitive values from log records before they reach handlers."""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        redacted = _API_KEY_PATTERN.sub("[REDACTED_API_KEY]", msg)
        redacted = _BEARER_PATTERN.sub("[REDACTED_TOKEN]", redacted)
        if redacted != msg:
            record.msg = redacted
            record.args = ()
        return True


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------
_initialised = False


def setup_logging(level: int = logging.INFO) -> None:
    global _initialised
    if _initialised:
        return
    _initialised = True

    ensure_dirs()
    root = logging.getLogger()
    root.setLevel(level)

    fmt = logging.Formatter(
        fmt="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Rotating file handler
    fh = RotatingFileHandler(
        LOGS_DIR / "app.log",
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5,
        encoding="utf-8",
    )
    fh.setFormatter(fmt)
    fh.addFilter(RedactingFilter())

    # Console handler
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    ch.addFilter(RedactingFilter())

    root.addHandler(fh)
    root.addHandler(ch)

    # Quiet noisy third-party loggers
    for noisy in ("urllib3", "httpx", "httpcore", "asyncio", "playwright"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


logger = logging.getLogger("ai-lead-generator")
