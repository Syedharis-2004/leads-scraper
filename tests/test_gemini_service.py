"""
Tests for the Gemini service: API key validation and prompt parsing.

All Gemini API calls are mocked — no real API quota is consumed.
"""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest

from services import gemini_service
from services.gemini_service import (
    GeminiKeyInvalidError,
    GeminiKeyMissingError,
    GeminiQuotaError,
    GeminiError,
    _categorise_exception,
    parse_prompt,
    validate_api_key,
)
from models.schemas import ApiKeyTestResponse, SearchConfig


# ---------------------------------------------------------------------------
# Mock genai Client helpers
# ---------------------------------------------------------------------------
class MockResponse:
    def __init__(self, text: str = "OK"):
        self.text = text


class MockGenAI:
    """Mock for the google.genai module."""

    def __init__(self, response_text="OK", raise_exc=None):
        self.response_text = response_text
        self.raise_exc = raise_exc
        self.models = MagicMock()
        self.models.generate_content = Mock(side_effect=self._generate_content)

    def _generate_content(self, model="", contents="", **kwargs):
        if self.raise_exc:
            raise self.raise_exc
        return MockResponse(self.response_text)

    def Client(self, api_key=""):
        return self


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------
def test_validate_no_key(temp_data_dir):
    """Validation returns invalid when no key is configured."""
    with patch("services.gemini_service.get_api_key", return_value=None):
        result = validate_api_key(api_key=None)
    assert result.valid is False
    assert "No API key" in result.message


def test_validate_valid_key(temp_data_dir):
    """A valid key produces a successful validation response."""
    mock_genai = MockGenAI(response_text="OK")
    with patch("services.gemini_service.get_api_key", return_value="fake-key"):
        with patch("services.gemini_service._import_genai", return_value=mock_genai):
            result = validate_api_key(api_key="fake-key", model="gemini-2.0-flash")
    assert result.valid is True
    assert result.model == "gemini-2.0-flash"
    mock_genai.models.generate_content.assert_called_once()


def test_validate_invalid_key(temp_data_dir):
    """An invalid key (permission denied) returns invalid."""
    exc = Exception("API key not valid. Please pass a valid API key.")
    mock_genai = MockGenAI(raise_exc=exc)
    with patch("services.gemini_service.get_api_key", return_value="fake-key"):
        with patch("services.gemini_service._import_genai", return_value=mock_genai):
            result = validate_api_key(api_key="fake-key")
    assert result.valid is False
    assert "invalid" in result.message.lower() or "API key" in result.message


def test_validate_quota_exceeded(temp_data_dir):
    """Quota exceeded error is categorised correctly."""
    exc = Exception("429 RESOURCE_EXHAUSTED: Quota exceeded for the request.")
    mock_genai = MockGenAI(raise_exc=exc)
    with patch("services.gemini_service.get_api_key", return_value="fake-key"):
        with patch("services.gemini_service._import_genai", return_value=mock_genai):
            result = validate_api_key(api_key="fake-key")
    assert result.valid is False
    assert "quota" in result.message.lower()


def test_validate_model_unavailable(temp_data_dir):
    """Model not found error is categorised correctly."""
    exc = Exception("404 NOT_FOUND: Model not found.")
    mock_genai = MockGenAI(raise_exc=exc)
    with patch("services.gemini_service.get_api_key", return_value="fake-key"):
        with patch("services.gemini_service._import_genai", return_value=mock_genai):
            result = validate_api_key(api_key="fake-key")
    assert result.valid is False
    assert "Model unavailable" in result.message or "not found" in result.message.lower()


def test_validate_network_error(temp_data_dir):
    """Network errors are categorised correctly."""
    exc = Exception("ConnectionError: Failed to establish connection.")
    mock_genai = MockGenAI(raise_exc=exc)
    with patch("services.gemini_service.get_api_key", return_value="fake-key"):
        with patch("services.gemini_service._import_genai", return_value=mock_genai):
            result = validate_api_key(api_key="fake-key")
    assert result.valid is False
    assert "Network" in result.message or "connection" in result.message.lower()


# ---------------------------------------------------------------------------
# Error categorisation tests
# ---------------------------------------------------------------------------
def test_categorise_permission_denied():
    err = _categorise_exception(Exception("403 PERMISSION_DENIED"))
    assert err.code == "PERMISSION_DENIED"


def test_categorise_quota():
    err = _categorise_exception(Exception("RESOURCE_EXHAUSTED: quota exceeded"))
    assert err.code == "QUOTA_EXCEEDED"


def test_categorise_rate_limit():
    err = _categorise_exception(Exception("429 rate limit exceeded"))
    assert err.code == "RATE_LIMIT"


def test_categorise_model_not_found():
    err = _categorise_exception(Exception("404 model not found"))
    assert err.code == "MODEL_UNAVAILABLE"


def test_categorise_network():
    err = _categorise_exception(Exception("Connection timeout"))
    assert err.code == "NETWORK"


def test_categorise_generic():
    err = _categorise_exception(Exception("Something unexpected happened"))
    assert err.code == "GEMINI_ERROR"


# ---------------------------------------------------------------------------
# Prompt parsing tests
# ---------------------------------------------------------------------------
def test_parse_prompt_success(temp_data_dir):
    """Prompt parsing returns a valid SearchConfig."""
    mock_response = MockResponse(json.dumps({
        "business_type": "Digital Marketing Agency",
        "location": "Karachi, Pakistan",
        "limit": 50,
        "fields": ["company_name", "owner_name", "website", "email", "phone", "city", "description"],
    }))
    mock_genai = MockGenAI()
    mock_genai.response_text = mock_response.text

    with patch("services.gemini_service.get_api_key", return_value="fake-key"):
        with patch("services.gemini_service._import_genai", return_value=mock_genai):
            config = parse_prompt("Find 50 digital marketing agencies in Karachi")

    assert config.business_type == "Digital Marketing Agency"
    assert config.location == "Karachi, Pakistan"
    assert config.limit == 50
    assert "company_name" in config.fields
    assert "email" in config.fields
    assert config.raw_prompt == "Find 50 digital marketing agencies in Karachi"


def test_parse_prompt_missing_key(temp_data_dir):
    """Prompt parsing raises when no API key is set."""
    with patch("services.gemini_service.get_api_key", return_value=None):
        with pytest.raises(GeminiKeyMissingError):
            parse_prompt("test prompt")


def test_parse_prompt_clamps_limit(temp_data_dir):
    """Limit is clamped to the valid range."""
    mock_response = MockResponse(json.dumps({
        "business_type": "Restaurant",
        "location": "Dubai",
        "limit": 500,  # over max
        "fields": ["company_name"],
    }))
    mock_genai = MockGenAI()
    mock_genai.response_text = mock_response.text

    with patch("services.gemini_service.get_api_key", return_value="fake-key"):
        with patch("services.gemini_service._import_genai", return_value=mock_genai):
            config = parse_prompt("Find 500 restaurants")
    assert config.limit == 200  # clamped to max


def test_parse_prompt_default_fields(temp_data_dir):
    """When no fields are specified, defaults are used."""
    mock_response = MockResponse(json.dumps({
        "business_type": "Cafe",
        "location": "London",
        "limit": 10,
        "fields": [],
    }))
    mock_genai = MockGenAI()
    mock_genai.response_text = mock_response.text

    with patch("services.gemini_service.get_api_key", return_value="fake-key"):
        with patch("services.gemini_service._import_genai", return_value=mock_genai):
            config = parse_prompt("Find cafes in London")
    assert len(config.fields) > 0
    assert "company_name" in config.fields


def test_parse_prompt_markdown_stripped(temp_data_dir):
    """Markdown code fences in the response are stripped before JSON parsing."""
    raw = '```json\n{"business_type": "Shop", "location": "NYC", "limit": 5, "fields": ["company_name"]}\n```'
    mock_genai = MockGenAI(response_text=raw)

    with patch("services.gemini_service.get_api_key", return_value="fake-key"):
        with patch("services.gemini_service._import_genai", return_value=mock_genai):
            config = parse_prompt("Find shops in NYC")
    assert config.business_type == "Shop"


def test_parse_prompt_api_error(temp_data_dir):
    """Prompt parsing raises the correct error type on API failure."""
    exc = Exception("429 RESOURCE_EXHAUSTED")
    mock_genai = MockGenAI(raise_exc=exc)

    with patch("services.gemini_service.get_api_key", return_value="fake-key"):
        with patch("services.gemini_service._import_genai", return_value=mock_genai):
            with pytest.raises(GeminiError):
                parse_prompt("test")


def test_parse_prompt_field_normalisation(temp_data_dir):
    """Field names are normalised to canonical names."""
    mock_response = MockResponse(json.dumps({
        "business_type": "Agency",
        "location": "Paris",
        "limit": 15,
        "fields": ["Business Name", "Phone Number", "Business Description"],
    }))
    mock_genai = MockGenAI()
    mock_genai.response_text = mock_response.text

    with patch("services.gemini_service.get_api_key", return_value="fake-key"):
        with patch("services.gemini_service._import_genai", return_value=mock_genai):
            config = parse_prompt("Find agencies in Paris")
    # Spaces should be replaced with underscores and mapped
    assert "company_name" in config.fields or "phone" in config.fields
