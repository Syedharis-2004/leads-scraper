"""
Scraping service: wraps ScrapeGraphAI's SmartScraperGraph.

For each discovered URL, a SmartScraperGraph is created with the user's
Gemini API key and a prompt that requests the business fields defined in
the search configuration.  Individual website failures are caught and
logged — one bad URL never kills the whole batch.
"""

import time
from typing import Callable, Optional

from config.settings import REQUEST_DELAY_SECONDS, SCRAPER_MAX_RETRIES, SCRAPER_TIMEOUT_SECONDS
from models.schemas import SearchConfig
from utils.logging_config import logger
from utils.security import redact_exception
from utils.secure_storage import get_api_key


class ScrapingError(Exception):
    pass


# ---------------------------------------------------------------------------
# Config builder
# ---------------------------------------------------------------------------
def _build_graph_config(api_key: str, model: str) -> dict:
    """
    Build a ScrapeGraphAI graph config dict for the given Gemini model.

    The model string uses the langchain provider convention:
        google_genai/<model_name>
    """
    # ScrapeGraphAI splits "provider/model" — google_genai is the provider.
    model_string = f"google_genai/{model}"

    return {
        "llm": {
            "model": model_string,
            "api_key": api_key,
        },
        "verbose": False,
        "headless": True,
        "timeout": SCRAPER_TIMEOUT_SECONDS,
        # Disable telemetry to avoid external network calls
    }


# ---------------------------------------------------------------------------
# Build the extraction prompt
# ---------------------------------------------------------------------------
def _build_extraction_prompt(config: SearchConfig) -> str:
    """Build the prompt sent to ScrapeGraphAI for each page."""
    field_descriptions = {
        "company_name": "Company / business name",
        "owner_name": "Owner or founder name (if publicly available)",
        "website": "Website URL",
        "email": "Public business email address",
        "phone": "Phone number",
        "city": "City",
        "country": "Country",
        "description": "Brief business description",
    }

    field_list = "\n".join(
        f"  - {f}: {field_descriptions.get(f, f)}"
        for f in config.fields
    )

    return (
        f"Extract the following business information from this webpage.\n"
        f"Only include information that is actually present on the page.\n"
        f"Do NOT fabricate or guess any missing information — leave it empty if not found.\n"
        f"Return a JSON object with these fields:\n{field_list}\n\n"
        f"Business type context: {config.business_type or 'any business'}\n"
        f"Location context: {config.location or 'any'}\n\n"
        f"Return ONLY the JSON object, no markdown or extra text."
    )


# ---------------------------------------------------------------------------
# Scrape a single URL
# ---------------------------------------------------------------------------
def scrape_url(
    url: str,
    config: SearchConfig,
    model: str,
    api_key: Optional[str] = None,
    max_retries: int = SCRAPER_MAX_RETRIES,
) -> dict:
    """
    Scrape a single URL and return extracted lead data as a dict.

    Raises ScrapingError on failure.
    """
    if api_key is None:
        api_key = get_api_key()
    if not api_key:
        raise ScrapingError("No API key configured")

    graph_config = _build_graph_config(api_key, model)
    prompt = _build_extraction_prompt(config)

    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            from scrapegraphai.graphs import SmartScraperGraph

            logger.info(f"Scraping {url} (attempt {attempt}/{max_retries})")

            graph = SmartScraperGraph(
                prompt=prompt,
                source=url,
                config=graph_config,
            )
            result = graph.run()

            if result and isinstance(result, dict):
                # Enrich with source URL
                result["source_url"] = url
                logger.info(f"Successfully scraped {url}: {len(result)} fields")
                return result
            elif result and isinstance(result, str):
                # Try to parse as JSON
                import json
                try:
                    parsed = json.loads(result)
                    parsed["source_url"] = url
                    return parsed
                except json.JSONDecodeError:
                    logger.warning(f"Scrape returned non-JSON string for {url}")
                    return {"source_url": url, "raw": result}
            else:
                logger.warning(f"Empty result for {url}")
                return {"source_url": url}

        except Exception as exc:
            last_error = exc
            redacted = redact_exception(exc, [api_key])
            logger.warning(f"Scrape failed for {url} (attempt {attempt}): {redacted}")
            if attempt < max_retries:
                time.sleep(2 * attempt)  # simple backoff

    error_msg = f"Failed to scrape {url} after {max_retries} attempts: "
    error_msg += redact_exception(last_error, [api_key])
    
    # Add helpful message for Playwright browser missing error
    if "Executable doesn't exist" in str(last_error) and "playwright" in str(last_error).lower():
        error_msg += "\n\nPLAYWRIGHT BROWSERS NOT INSTALLED!"
        error_msg += "\nThe web scraper needs Playwright browsers to scrape websites."
        error_msg += "\nTo fix this, run: python -m playwright install"
        error_msg += "\nThis will download ~100MB of browser files and may take a few minutes."
    
    raise ScrapingError(error_msg)


# ---------------------------------------------------------------------------
# Batch scraping with progress callback
# ---------------------------------------------------------------------------
def scrape_batch(
    urls: list[str],
    config: SearchConfig,
    model: str,
    api_key: Optional[str] = None,
    on_progress: Optional[Callable[[int, int, Optional[dict], Optional[str]], None]] = None,
    should_cancel: Optional[Callable[[], bool]] = None,
) -> tuple[list[dict], list[str]]:
    """
    Scrape multiple URLs sequentially.

    Calls ``on_progress(index, total, lead_data_or_None, error_or_None)``
    after each URL.

    Returns ``(successful_leads, failed_urls)``.
    """
    successful: list[dict] = []
    failed: list[str] = []
    total = len(urls)

    for i, url in enumerate(urls):
        if should_cancel and should_cancel():
            logger.info("Scraping cancelled by user")
            break

        lead: dict | None = None
        error: str | None = None

        try:
            lead = scrape_url(url, config, model, api_key)
            successful.append(lead)
        except ScrapingError as exc:
            error = str(exc)
            failed.append(url)
            logger.warning(f"URL failed: {url} -> {error}")
        except Exception as exc:
            error = redact_exception(exc, [api_key] if api_key else None)
            failed.append(url)
            logger.error(f"Unexpected error scraping {url}: {error}")

        # Progress callback
        if on_progress:
            on_progress(i + 1, total, lead, error)

        # Delay between requests (respect rate limits)
        if i < total - 1:
            time.sleep(REQUEST_DELAY_SECONDS)

    logger.info(f"Batch complete: {len(successful)} successful, {len(failed)} failed")
    return successful, failed
