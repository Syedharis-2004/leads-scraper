"""
Activity logs route.

Reads the last N lines from logs/app.log and returns them to the dashboard.
Secrets in log lines are already redacted by the RedactingFilter, but we
apply an additional pass here for safety.
"""

import re
from collections import deque
from pathlib import Path

from fastapi import APIRouter, Query

from config.settings import LOGS_DIR
from models.schemas import ActivityEntry, ActivityLogResponse
from utils.security import redact_secrets

router = APIRouter(prefix="/api/logs", tags=["logs"])

# Regex to parse log lines: "2024-01-01 12:00:00  INFO  logger  message"
_LOG_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+(\w+)\s+(.+?)\s{2,}(.*)$"
)


def _parse_log_line(line: str) -> ActivityEntry | None:
    """Parse a log line into an ActivityEntry."""
    line = line.rstrip("\n\r")
    if not line.strip():
        return None
    match = _LOG_RE.match(line)
    if match:
        return ActivityEntry(
            timestamp=match.group(1),
            level=match.group(2),
            message=redact_secrets(match.group(4)),
        )
    # Non-standard line
    return ActivityEntry(
        timestamp="",
        level="INFO",
        message=redact_secrets(line),
    )


@router.get("", response_model=ActivityLogResponse)
def get_logs(
    lines: int = Query(200, ge=1, le=5000, description="Number of log lines"),
    level: str = Query("", description="Filter by level (INFO, WARNING, ERROR)"),
):
    """Return recent application logs."""
    log_file = LOGS_DIR / "app.log"
    entries: list[ActivityEntry] = []

    if log_file.exists():
        # Read the last N lines efficiently
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            all_lines = deque(f, maxlen=lines * 2)  # read a bit extra for filtering

        for line in all_lines:
            entry = _parse_log_line(line)
            if entry:
                if level and entry.level != level.upper():
                    continue
                entries.append(entry)

        entries = entries[-lines:]

    return ActivityLogResponse(
        entries=entries,
        total=len(entries),
    )
