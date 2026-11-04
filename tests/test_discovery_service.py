"""
Tests for the discovery service.

DuckDuckGo search is mocked so tests don't make real network requests.
"""

from unittest.mock import Mock, patch

import pytest

from services import discovery_service
from models.schemas import SearchConfig
from utils.security import validate_url


def test_validate_url_valid():
    assert validate_url("https://example.com") is True
    assert validate_url("http://example.com/path") is True


def test_validate_url_invalid():
    assert validate_url("") is False
    assert validate_url("not a url") is False
    assert validate_url("ftp://example.com") is False
    assert validate_url("javascript:alert(1)") is False


def test_build_search_query():
    config = SearchConfig(business_type="Digital Marketing Agency", location="Karachi, Pakistan")
    query = discovery_service._build_search_query(config)
    assert "Digital Marketing Agency" in query
    assert "Karachi" in query


def test_build_search_query_empty():
    config = SearchConfig(business_type="", location="")
    query = discovery_service._build_search_query(config)
    assert "business" in query


def _make_mock_ddgs(mock_results):
    """Create a mock DDGS context manager that returns *mock_results*."""
    instance = Mock()
    instance.text = Mock(return_value=mock_results)
    manager = Mock()
    manager.__enter__ = Mock(return_value=instance)
    manager.__exit__ = Mock(return_value=None)
    return manager


def test_search_businesses_mocked():
    """Discovery returns valid URLs from mocked search results."""
    config = SearchConfig(business_type="Cafe", location="London", limit=5)

    mock_results = [
        {"href": "https://cafe1.com", "title": "Cafe 1", "body": "Great cafe"},
        {"href": "https://cafe2.com", "title": "Cafe 2", "body": "Another cafe"},
        {"href": "https://cafe3.com", "title": "Cafe 3", "body": "Third cafe"},
    ]

    with patch.object(discovery_service, "DDGS") as MockDDGS:
        MockDDGS.return_value = _make_mock_ddgs(mock_results)
        results = discovery_service.search_businesses(config, max_results=5)

    assert len(results) == 3
    assert results[0]["url"] == "https://cafe1.com"
    assert results[0]["title"] == "Cafe 1"


def test_search_deduplicates_urls():
    """Duplicate URLs (after normalisation) are removed."""
    config = SearchConfig(business_type="Shop", location="NYC", limit=10)

    mock_results = [
        {"href": "https://shop.com", "title": "Shop", "body": "1"},
        {"href": "https://shop.com/", "title": "Shop dup", "body": "2"},
        {"href": "https://www.shop.com", "title": "Shop www", "body": "3"},
        {"href": "https://other.com", "title": "Other", "body": "4"},
    ]

    with patch.object(discovery_service, "DDGS") as MockDDGS:
        MockDDGS.return_value = _make_mock_ddgs(mock_results)
        results = discovery_service.search_businesses(config, max_results=10)

    # shop.com, shop.com/, www.shop.com all normalise to the same key
    assert len(results) == 2
    assert results[0]["url"] == "https://shop.com"
    assert results[1]["url"] == "https://other.com"


def test_url_normalisation():
    """URL normalisation strips www, trailing slash, and lowercases host."""
    n1 = discovery_service._normalise_url("https://www.example.com/")
    n2 = discovery_service._normalise_url("https://example.com")
    assert n1 == n2


def test_validate_urls():
    urls = ["https://valid.com", "invalid", "http://also-valid.com", ""]
    valid = discovery_service.validate_urls(urls)
    assert len(valid) == 2


def test_search_filters_invalid_urls():
    """Invalid URLs are filtered out of search results."""
    config = SearchConfig(business_type="Test", location="Test", limit=5)

    mock_results = [
        {"href": "https://valid.com", "title": "Valid", "body": "ok"},
        {"href": "not-a-url", "title": "Invalid", "body": "bad"},
        {"href": "", "title": "Empty", "body": "empty"},
    ]

    with patch.object(discovery_service, "DDGS") as MockDDGS:
        MockDDGS.return_value = _make_mock_ddgs(mock_results)
        results = discovery_service.search_businesses(config, max_results=5)

    assert len(results) == 1
    assert results[0]["url"] == "https://valid.com"


def test_search_respects_limit():
    """Search returns at most *limit* results."""
    config = SearchConfig(business_type="Test", location="Test", limit=3)

    mock_results = [
        {"href": f"https://site{i}.com", "title": f"Site {i}", "body": "desc"}
        for i in range(20)
    ]

    with patch.object(discovery_service, "DDGS") as MockDDGS:
        MockDDGS.return_value = _make_mock_ddgs(mock_results)
        results = discovery_service.search_businesses(config, max_results=3)

    assert len(results) == 3


def test_search_failure_raises():
    """Discovery errors are propagated."""
    config = SearchConfig(business_type="Test", location="Test", limit=5)

    with patch.object(discovery_service, "DDGS") as MockDDGS:
        manager = Mock()
        manager.__enter__ = Mock(side_effect=Exception("Network down"))
        manager.__exit__ = Mock(return_value=None)
        MockDDGS.return_value = manager

        with pytest.raises(discovery_service.DiscoveryError):
            discovery_service.search_businesses(config)
