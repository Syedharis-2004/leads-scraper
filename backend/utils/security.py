"""
Security utilities: input sanitisation, path-traversal prevention,
and secret redaction for exception traces.
"""

import re
import unicodedata
from typing import Any

# ---------------------------------------------------------------------------
# Secret redaction
# ---------------------------------------------------------------------------
_REDACT_PLACEHOLDER = "[REDACTED]"


def redact_secrets(text: str, secret_values: list[str] | None = None) -> str:
    """
    Replace any known secret value that appears in *text* with a placeholder.
    Also catches Gemini-style API keys (AIza...) heuristically.
    """
    if not text:
        return text
    result = text
    if secret_values:
        for sv in secret_values:
            if sv and len(sv) > 8:
                result = result.replace(sv, _REDACT_PLACEHOLDER)
    # heuristic: AIza... keys
    result = re.sub(r"AIza[0-9A-Za-z\-_]{20,}", _REDACT_PLACEHOLDER, result)
    return result


def redact_exception(exc: BaseException, secret_values: list[str] | None = None) -> str:
    """Return a redacted string representation of an exception."""
    return redact_secrets(str(exc), secret_values)


# ---------------------------------------------------------------------------
# Input sanitisation
# ---------------------------------------------------------------------------
_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._\-]")


def sanitize_filename(name: str, max_len: int = 255) -> str:
    """Sanitise a string so it is safe to use as a filename."""
    name = unicodedata.normalize("NFKD", name)
    name = name.encode("ascii", "ignore").decode("ascii")
    name = _SAFE_FILENAME_RE.sub("_", name)
    return name[:max_len].strip("._") or "untitled"


def validate_url(url: str) -> bool:
    """Basic validation that a string looks like an http(s) URL."""
    if not url or not isinstance(url, str):
        return False
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def is_safe_path(base_dir: str, target: str) -> bool:
    """
    Ensure *target* (after normalisation) stays inside *base_dir*.
    Guards against path-traversal attacks.
    """
    import os
    base = os.path.abspath(base_dir)
    full = os.path.abspath(os.path.join(base, target))
    return os.path.commonpath([base, full]) == base


def truncate_for_display(text: Any, max_len: int = 500) -> str:
    """Safely truncate arbitrary text for display in logs or responses."""
    s = str(text) if text is not None else ""
    return s[:max_len] + ("…" if len(s) > max_len else "")
