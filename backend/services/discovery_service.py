"""
Business discovery service.

Uses DuckDuckGo Search (via the *ddgs* package, which ships with
ScrapeGraphAI) to find relevant business websites based on a structured
search configuration.

This is a SEPARATE discovery stage — we do not rely on ScrapeGraphAI's
SearchGraph to provide unrestricted internet search.  Instead we search
first, validate URLs, then pass them to the scraping engine.
"""

import time
from typing import Optional
from urllib.parse import urlparse

from models.schemas import SearchConfig
from utils.logging_config import logger
from utils.security import validate_url

# DDGS is a dependency of scrapegraphai; imported at module level
# so tests can patch services.discovery_service.DDGS.
try:
    from ddgs import DDGS
except ImportError:
    DDGS = None


class DiscoveryError(Exception):
    pass


def _build_search_query(config: SearchConfig) -> str:
    """Build a DuckDuckGo search query from the structured config."""
    parts = []
    if config.business_type:
        parts.append(config.business_type)
    if config.location:
        parts.append(f"in {config.location}")
    return " ".join(parts) if parts else "business"


def search_businesses(
    config: SearchConfig,
    max_results: Optional[int] = None,
) -> list[dict]:
    """
    Search for businesses matching *config*.

    Returns a list of dicts: ``{url, title, description}``.

    Raises DiscoveryError on total failure (network, library missing).
    Individual search failures are logged and skipped.
    """
    query = _build_search_query(config)
    limit = max_results or config.limit
    logger.info(f"Discovering businesses: query='{query}', max={limit}")

    try:
        if DDGS is None:
            raise DiscoveryError(
            "ddgs package not installed (should come with scrapegraphai)"
        )
    except DiscoveryError:
        raise
    except Exception as exc:
        raise DiscoveryError(
            "ddgs package not installed (should come with scrapegraphai)"
        ) from exc

    results: list[dict] = []
    try:
        with DDGS() as ddgs:
            # ddgs.text returns generator; each item: {title, href, body}
            raw_results = list(ddgs.text(query, max_results=limit * 3))
    except Exception as exc:
        logger.error(f"DuckDuckGo search failed: {exc}")
        raise DiscoveryError(f"Search failed: {exc}") from exc

    # Validate and deduplicate URLs
    seen_urls: set[str] = set()
    for item in raw_results:
        url = item.get("href") or item.get("url") or ""
        if not url:
            continue
        url = url.strip()
        if not validate_url(url):
            continue

        # Normalise for dedup
        normalised = _normalise_url(url)
        if normalised in seen_urls:
            continue
        seen_urls.add(normalised)

        results.append({
            "url": url,
            "title": item.get("title", ""),
            "description": item.get("body") or item.get("description", ""),
        })

        if len(results) >= limit:
            break

    logger.info(f"Discovered {len(results)} unique business URLs")
    return results


def _normalise_url(url: str) -> str:
    """Normalise a URL for deduplication (strip trailing slash, lowercase host)."""
    parsed = urlparse(url)
    host = parsed.netloc.lower().replace("www.", "")
    path = parsed.path.rstrip("/")
    return f"{parsed.scheme}://{host}{path}"


def validate_urls(urls: list[str]) -> list[str]:
    """Filter a list of URLs, keeping only valid http(s) URLs."""
    return [u for u in urls if validate_url(u)]
