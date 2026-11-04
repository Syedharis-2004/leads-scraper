"""
Gemini service: API key validation and natural-language prompt parsing.

Uses the official google-generativeai SDK directly (not via ScrapeGraphAI)
so that key validation and prompt interpretation are independent of the
scraping pipeline.
"""

import json
import re
from typing import Optional

from config.settings import AVAILABLE_GEMINI_MODELS, DEFAULT_GEMINI_MODEL
from models.schemas import ApiKeyTestResponse, SearchConfig
from utils.logging_config import logger
from utils.security import redact_exception
from utils.secure_storage import get_api_key


# ---------------------------------------------------------------------------
# Error categorisation
# ---------------------------------------------------------------------------
class GeminiError(Exception):
    """Base error with a user-friendly message and a code."""
    def __init__(self, message: str, code: str = "GEMINI_ERROR", detail: str = ""):
        super().__init__(message)
        self.code = code
        self.detail = detail
        self.message = message


class GeminiKeyMissingError(GeminiError):
    def __init__(self):
        super().__init__("No API key configured", code="KEY_MISSING")


class GeminiKeyInvalidError(GeminiError):
    def __init__(self, detail: str = ""):
        super().__init__("Invalid API key", code="KEY_INVALID", detail=detail)


class GeminiQuotaError(GeminiError):
    def __init__(self, detail: str = ""):
        super().__init__("Gemini quota exceeded", code="QUOTA_EXCEEDED", detail=detail)


class GeminiRateLimitError(GeminiError):
    def __init__(self, detail: str = ""):
        super().__init__("Gemini rate limit exceeded", code="RATE_LIMIT", detail=detail)


class GeminiModelError(GeminiError):
    def __init__(self, model: str = "", detail: str = ""):
        super().__init__(
            f"Model unavailable: {model}", code="MODEL_UNAVAILABLE", detail=detail
        )


class GeminiNetworkError(GeminiError):
    def __init__(self, detail: str = ""):
        super().__init__("Network error reaching Gemini API", code="NETWORK", detail=detail)


class GeminiPermissionError(GeminiError):
    def __init__(self, detail: str = ""):
        super().__init__("Permission denied by Gemini API", code="PERMISSION_DENIED", detail=detail)


class GeminiServiceError(GeminiError):
    def __init__(self, detail: str = ""):
        super().__init__("Gemini API service error", code="SERVICE_ERROR", detail=detail)


def _categorise_exception(exc: Exception) -> GeminiError:
    """Map a raw exception to one of our typed errors."""
    exc_str = str(exc)
    exc_type = type(exc).__name__

    # Check for common patterns
    lower = exc_str.lower()

    if ("api_key" in lower or "api key" in lower) and ("invalid" in lower or "not valid" in lower or "not a valid" in lower):
        return GeminiKeyInvalidError(redact_exception(exc))
    if "permission" in lower or "forbidden" in lower or "403" in lower:
        if "quota" in lower or "resource" in lower:
            return GeminiQuotaError(redact_exception(exc))
        return GeminiPermissionError(redact_exception(exc))
    if "resource_exhausted" in lower or "quota" in lower or "429" in lower:
        if "rate" in lower:
            return GeminiRateLimitError(redact_exception(exc))
        return GeminiQuotaError(redact_exception(exc))
    if "not found" in lower or "404" in lower or "model" in lower and "not" in lower:
        return GeminiModelError(detail=redact_exception(exc))
    if "unavailable" in lower or "503" in lower or "connection" in lower or "timeout" in lower:
        return GeminiNetworkError(redact_exception(exc))
    if "internal" in lower or "500" in lower or "502" in lower or "504" in lower:
        return GeminiServiceError(redact_exception(exc))

    # Generic fallback
    return GeminiError(
        message="Gemini API error",
        code="GEMINI_ERROR",
        detail=redact_exception(exc),
    )


# ---------------------------------------------------------------------------
# SDK import (lazy) — use the unified google-genai SDK
# ---------------------------------------------------------------------------
def _import_genai():
    """Import google.genai, raising a clear error if missing."""
    try:
        from google import genai
        return genai
    except ImportError as exc:
        raise GeminiError(
            "google-genai package is not installed",
            code="DEPENDENCY_MISSING",
            detail=str(exc),
        ) from exc


# ---------------------------------------------------------------------------
# API key validation
# ---------------------------------------------------------------------------
def validate_api_key(api_key: str | None = None, model: str | None = None) -> ApiKeyTestResponse:
    """
    Test the Gemini API key by making a real (minimal) API call.

    Returns an ApiKeyTestResponse.  Never raises – callers get a structured
    response with valid=False on failure.
    """
    # Resolve key
    if api_key is None:
        api_key = get_api_key()
    if not api_key:
        return ApiKeyTestResponse(
            valid=False, model=model or DEFAULT_GEMINI_MODEL,
            message="No API key configured",
            detail="Please save your Google AI Studio API key first.",
        )

    if model is None:
        from config.settings import AppConfig
        model = AppConfig.get().gemini_model

    logger.info(f"Validating Gemini API key (model={model})")

    try:
        genai = _import_genai()
        client = genai.Client(api_key=api_key)

        # Use the test model for validation (cheaper). Fall back to requested model.
        test_model_name = model if model in AVAILABLE_GEMINI_MODELS else DEFAULT_GEMINI_MODEL

        # Minimal generate call
        response = client.models.generate_content(
            model=test_model_name,
            contents="Reply with the single word: OK",
        )

        # Check we got a valid response
        text = ""
        try:
            text = response.text
        except Exception:
            # Some responses may have no text (blocked, etc.)
            text = ""

        if text or response:
            logger.info("Gemini API key validation succeeded")
            return ApiKeyTestResponse(
                valid=True,
                model=test_model_name,
                message="API key is valid and working",
            )

    except GeminiError:
        raise
    except Exception as exc:
        typed = _categorise_exception(exc)
        logger.warning(f"Gemini API key validation failed: {typed.code} - {typed.message}")
        return ApiKeyTestResponse(
            valid=False,
            model=model or DEFAULT_GEMINI_MODEL,
            message=typed.message,
            detail=typed.detail,
        )

    return ApiKeyTestResponse(
        valid=False, model=model or DEFAULT_GEMINI_MODEL,
        message="Validation failed for unknown reason",
    )


# ---------------------------------------------------------------------------
# Prompt parsing
# ---------------------------------------------------------------------------
_PROMPT_PARSE_INSTRUCTION = """\
You are a lead-generation assistant.  Analyse the user's request and extract
a structured JSON configuration.

Return ONLY valid JSON (no markdown, no explanation) with these fields:
{
  "business_type": "<the type of business, e.g. 'Digital Marketing Agency'>",
  "location": "<city and/or country, e.g. 'Karachi, Pakistan'>",
  "limit": <number of leads requested, default 25, max 200>,
  "fields": ["<list of data fields to extract>"]
}

Map common field names to these canonical names:
  - company name  -> "company_name"
  - owner name    -> "owner_name"
  - website       -> "website"
  - email         -> "email"
  - phone number  -> "phone"
  - city          -> "city"
  - country       -> "country"
  - description    -> "description"

If the user does not specify a number, use 25.
If the user does not specify fields, use all of: company_name, owner_name,
website, email, phone, city, description.
"""

_PROMPT_PARSE_FALLBACK_INSTRUCTION = """\
Return ONLY the JSON.  No markdown code fences, no extra text."""


def parse_prompt(prompt: str, model: str | None = None) -> SearchConfig:
    """
    Use Gemini to interpret a natural-language prompt and produce a
    structured SearchConfig.

    Raises GeminiError subclass on failure.
    """
    api_key = get_api_key()
    if not api_key:
        raise GeminiKeyMissingError()

    if model is None:
        from config.settings import AppConfig
        model = AppConfig.get().gemini_model

    logger.info(f"Parsing prompt with Gemini (model={model}): {prompt[:100]}...")

    genai = _import_genai()
    client = genai.Client(api_key=api_key)

    full_prompt = (
        f"{_PROMPT_PARSE_INSTRUCTION}\n\n"
        f"{_PROMPT_PARSE_FALLBACK_INSTRUCTION}\n\n"
        f"User request: {prompt}"
    )

    try:
        response = client.models.generate_content(
            model=model,
            contents=full_prompt,
        )
        raw_text = response.text.strip()
    except GeminiError:
        raise
    except Exception as exc:
        raise _categorise_exception(exc) from exc

    # Strip markdown fences if present
    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
    raw_text = re.sub(r"\s*```$", "", raw_text)

    logger.info(f"Gemini prompt parse response: {raw_text[:300]}")

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        # Try to extract JSON from the text
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group())
            except json.JSONDecodeError as exc:
                raise GeminiError(
                    "Failed to parse Gemini response as JSON",
                    code="PARSE_ERROR",
                    detail=str(exc),
                ) from exc
        else:
            raise GeminiError(
                "Gemini response did not contain valid JSON",
                code="PARSE_ERROR",
            ) from exc

    # Validate and normalise
    business_type = str(parsed.get("business_type", "")).strip()
    location = str(parsed.get("location", "")).strip()
    limit = parsed.get("limit", 25)
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 25
    limit = max(1, min(200, limit))

    fields = parsed.get("fields", [])
    if not isinstance(fields, list):
        fields = []
    # Normalise field names to canonical names
    field_map = {
        "company_name": "company_name",
        "owner_name": "owner_name",
        "website": "website",
        "email": "email",
        "phone": "phone",
        "phone_number": "phone",
        "city": "city",
        "country": "country",
        "description": "description",
        "business_description": "description",
    }
    canonical_fields: list[str] = []
    for f in fields:
        key = str(f).strip().lower().replace(" ", "_")
        canonical = field_map.get(key, key)
        if canonical not in canonical_fields:
            canonical_fields.append(canonical)

    if not canonical_fields:
        canonical_fields = ["company_name", "owner_name", "website", "email",
                           "phone", "city", "description"]

    config = SearchConfig(
        business_type=business_type,
        location=location,
        limit=limit,
        fields=canonical_fields,
        raw_prompt=prompt,
    )

    logger.info(f"Parsed search config: type={business_type}, location={location}, "
                f"limit={limit}, fields={canonical_fields}")
    return config
