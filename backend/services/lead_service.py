"""
Lead generation service: orchestrates the full pipeline.

Pipeline:
    User Prompt
      -> Gemini prompt understanding (structured search config)
      -> Business discovery (DuckDuckGo search)
      -> URL validation
      -> ScrapeGraphAI (per-URL scraping)
      -> Data validation
      -> Duplicate detection
      -> CSV storage
      -> Dashboard display

Progress is tracked in-memory per job so the frontend can poll for updates.
Cancellation is supported via a per-job flag.
"""

import threading
import time
import uuid
from datetime import datetime
from typing import Optional

from config.settings import DEFAULT_GEMINI_MODEL
from models.schemas import GenerationStatusResponse, SearchConfig
from services import csv_service, discovery_service, scraping_service
from services.gemini_service import GeminiError, parse_prompt
from utils.logging_config import logger
from utils.secure_storage import get_api_key


# ---------------------------------------------------------------------------
# Job manager (in-memory, thread-safe)
# ---------------------------------------------------------------------------
class JobStatus:
    """Mutable status container for a single generation job."""

    def __init__(self, job_id: str) -> None:
        self.job_id = job_id
        self.stage: str = "init"
        self.message: str = ""
        self.total_websites: int = 0
        self.websites_discovered: int = 0
        self.websites_processed: int = 0
        self.leads_extracted: int = 0
        self.duplicates_skipped: int = 0
        self.failed_websites: int = 0
        self.failed_urls: list[str] = []
        self.progress: float = 0.0
        self.is_running: bool = False
        self.is_completed: bool = False
        self.is_cancelled: bool = False
        self.error: str = ""
        self.search_config: Optional[SearchConfig] = None
        self.new_lead_ids: list[str] = []
        self._cancel_flag = False
        self._lock = threading.Lock()

    def cancel(self) -> None:
        with self._lock:
            self._cancel_flag = True

    @property
    def cancelled(self) -> bool:
        with self._lock:
            return self._cancel_flag

    def to_response(self) -> GenerationStatusResponse:
        return GenerationStatusResponse(
            job_id=self.job_id,
            stage=self.stage,
            message=self.message,
            total_websites=self.total_websites,
            websites_discovered=self.websites_discovered,
            websites_processed=self.websites_processed,
            leads_extracted=self.leads_extracted,
            duplicates_skipped=self.duplicates_skipped,
            failed_websites=self.failed_websites,
            failed_urls=self.failed_urls,
            progress=self.progress,
            is_running=self.is_running,
            is_completed=self.is_completed,
            is_cancelled=self.is_cancelled,
            error=self.error,
            search_config=self.search_config,
            new_lead_ids=self.new_lead_ids,
        )


class JobManager:
    """Thread-safe registry of generation jobs."""

    _instance: "JobManager | None" = None
    _lock = threading.Lock()

    def __new__(cls) -> "JobManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._jobs: dict[str, JobStatus] = {}
        return cls._instance

    def create_job(self) -> JobStatus:
        job_id = uuid.uuid4().hex[:12]
        job = JobStatus(job_id)
        with self._lock:
            self._jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> Optional[JobStatus]:
        with self._lock:
            return self._jobs.get(job_id)

    def cancel_job(self, job_id: str) -> bool:
        job = self.get_job(job_id)
        if job and job.is_running:
            job.cancel()
            return True
        return False

    def clear_job(self, job_id: str) -> None:
        with self._lock:
            self._jobs.pop(job_id, None)

    def all_jobs(self) -> list[str]:
        with self._lock:
            return list(self._jobs.keys())


def get_job_manager() -> JobManager:
    return JobManager()


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
def run_generation_pipeline(prompt: str, job: JobStatus) -> None:
    """
    Run the full lead generation pipeline for *prompt*.
    Updates *job* in-place as it progresses.
    Designed to be called in a background thread.
    """
    api_key = get_api_key()
    if not api_key:
        job.error = "No API key configured. Please add your Gemini API key in Settings."
        job.stage = "error"
        job.is_running = False
        job.is_completed = True
        csv_service.record_search(success=False)
        return

    # Determine which Gemini model to use
    from config.settings import AppConfig
    model = AppConfig.get().gemini_model

    # ---- Stage 1: Parse prompt ----
    job.stage = "parsing_prompt"
    job.message = "Interpreting your prompt with Gemini..."
    job.is_running = True
    logger.info(f"[{job.job_id}] Stage: parsing prompt")

    try:
        search_config = parse_prompt(prompt, model=model)
        job.search_config = search_config
        job.message = (
            f"Looking for {search_config.business_type or 'businesses'}"
            f"{' in ' + search_config.location if search_config.location else ''}"
            f" (target: {search_config.limit})"
        )
    except GeminiError as exc:
        job.error = f"{exc.message}. {exc.detail}".strip()
        job.stage = "error"
        job.is_running = False
        job.is_completed = True
        csv_service.record_search(success=False)
        logger.error(f"[{job.job_id}] Prompt parse failed: {exc.code}")
        return

    if job.cancelled:
        job.is_cancelled = True
        job.is_running = False
        job.is_completed = True
        job.stage = "cancelled"
        return

    # ---- Stage 2: Discover businesses ----
    job.stage = "discovering"
    job.message = "Discovering relevant business websites..."
    job.progress = 5.0
    logger.info(f"[{job.job_id}] Stage: discovery")

    try:
        results = discovery_service.search_businesses(search_config)
        urls = [r["url"] for r in results]
        job.total_websites = len(urls)
        job.websites_discovered = len(urls)
        job.progress = 15.0

        if not urls:
            job.error = "No businesses found for your query. Try a more specific prompt."
            job.stage = "error"
            job.is_running = False
            job.is_completed = True
            csv_service.record_search(success=False)
            logger.warning(f"[{job.job_id}] No URLs discovered")
            return

        job.message = f"Found {len(urls)} websites. Starting extraction..."

    except Exception as exc:
        job.error = f"Discovery failed: {exc}"
        job.stage = "error"
        job.is_running = False
        job.is_completed = True
        csv_service.record_search(success=False)
        logger.error(f"[{job.job_id}] Discovery failed: {exc}")
        return

    if job.cancelled:
        job.is_cancelled = True
        job.is_running = False
        job.is_completed = True
        job.stage = "cancelled"
        return

    # ---- Stage 3: Scrape ----
    job.stage = "scraping"
    job.message = f"Scraping {len(urls)} websites..."
    logger.info(f"[{job.job_id}] Stage: scraping {len(urls)} URLs")

    existing_keys = csv_service.get_existing_keys()

    def on_progress(index: int, total: int, lead: dict | None, error: str | None) -> None:
        job.websites_processed = index
        # Progress: 15% -> 85% across scraping stage
        scrape_progress = (index / total) * 70.0 if total else 0
        job.progress = 15.0 + scrape_progress

        if error:
            job.failed_websites += 1
            # We don't have the URL here directly, get it from the URLs list
            if index - 1 < len(urls):
                job.failed_urls.append(urls[index - 1])

    try:
        successful_leads, failed_urls = scraping_service.scrape_batch(
            urls=urls,
            config=search_config,
            model=model,
            api_key=api_key,
            on_progress=on_progress,
            should_cancel=lambda: job.cancelled,
        )
    except Exception as exc:
        job.error = f"Scraping pipeline error: {exc}"
        job.stage = "error"
        job.is_running = False
        job.is_completed = True
        csv_service.record_search(success=False)
        logger.error(f"[{job.job_id}] Scraping error: {exc}")
        return

    if job.cancelled:
        job.is_cancelled = True
        job.is_running = False
        job.is_completed = True
        job.stage = "cancelled"
        csv_service.record_search(success=False)
        return

    job.failed_urls = failed_urls
    job.failed_websites = len(failed_urls)

    # ---- Stage 4: Data validation & normalisation ----
    job.stage = "validating"
    job.message = "Validating extracted data..."
    job.progress = 87.0

    normalised_leads: list[dict] = []
    for raw in successful_leads:
        lead = _normalise_lead(raw, search_config)
        if lead:
            normalised_leads.append(lead)

    # ---- Stage 5: Dedup & CSV storage ----
    job.stage = "saving"
    job.message = "Saving leads to CSV..."
    job.progress = 90.0

    try:
        added, skipped = csv_service.append_leads(
            normalised_leads,
            search_query=prompt,
            existing_keys=existing_keys,
        )
        job.leads_extracted = len(added)
        job.duplicates_skipped = skipped
        job.new_lead_ids = [l["lead_id"] for l in added]
        job.progress = 95.0
    except Exception as exc:
        job.error = f"Failed to save leads: {exc}"
        job.stage = "error"
        job.is_running = False
        job.is_completed = True
        csv_service.record_search(success=False)
        logger.error(f"[{job.job_id}] CSV save failed: {exc}")
        return

    # ---- Done ----
    job.stage = "complete"
    job.progress = 100.0
    job.is_running = False
    job.is_completed = True
    success = job.leads_extracted > 0
    csv_service.record_search(success=success)
    job.message = (
        f"Complete! Extracted {job.leads_extracted} leads, "
        f"skipped {job.duplicates_skipped} duplicates, "
        f"{job.failed_websites} websites failed."
    )
    logger.info(f"[{job.job_id}] Pipeline complete: {job.leads_extracted} leads")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _normalise_lead(raw: dict, config: SearchConfig) -> dict | None:
    """
    Normalise a raw scraped dict into our CSV column schema.
    Returns None if the lead has no useful data at all.
    """
    # Map common field name variants to canonical names
    field_map = {
        "company_name": "company_name",
        "name": "company_name",
        "business_name": "company_name",
        "company": "company_name",
        "owner_name": "owner_name",
        "owner": "owner_name",
        "founder": "owner_name",
        "founders": "owner_name",
        "ceo": "owner_name",
        "website": "website",
        "url": "website",
        "email": "email",
        "email_address": "email",
        "business_email": "email",
        "phone": "phone",
        "phone_number": "phone",
        "telephone": "phone",
        "contact": "phone",
        "city": "city",
        "country": "country",
        "description": "description",
        "business_description": "description",
        "about": "description",
        "source_url": "source_url",
    }

    lead: dict[str, str] = {}
    for csv_col in [
        "company_name", "owner_name", "website", "email",
        "phone", "city", "country", "business_type",
        "description", "source_url",
    ]:
        lead[csv_col] = ""

    for key, value in raw.items():
        canonical = field_map.get(str(key).strip().lower().replace(" ", "_"))
        if canonical and canonical in lead:
            existing = lead[canonical]
            if not existing:
                lead[canonical] = str(value).strip() if value else ""

    # Set business_type from search config if empty
    if not lead["business_type"]:
        lead["business_type"] = config.business_type

    # Set source_url if missing
    if not lead["source_url"]:
        lead["source_url"] = raw.get("source_url", "")

    # Validate email format
    if lead["email"]:
        import re
        if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", lead["email"]):
            lead["email"] = ""  # invalid email, clear it

    # Normalise website URL
    if lead["website"] and not lead["website"].startswith("http"):
        lead["website"] = "https://" + lead["website"]

    # Check if there's any meaningful data
    meaningful_fields = ["company_name", "website", "email", "phone", "description"]
    has_data = any(lead.get(f, "") for f in meaningful_fields)
    if not has_data:
        return None

    return lead


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def start_generation(prompt: str) -> str:
    """Start a generation job in a background thread.  Returns job_id."""
    manager = get_job_manager()
    job = manager.create_job()

    thread = threading.Thread(
        target=run_generation_pipeline,
        args=(prompt, job),
        daemon=True,
    )
    thread.start()

    logger.info(f"Started generation job {job.job_id} for prompt: {prompt[:80]}...")
    return job.job_id


def get_status(job_id: str) -> Optional[GenerationStatusResponse]:
    """Get the current status of a generation job."""
    manager = get_job_manager()
    job = manager.get_job(job_id)
    if job is None:
        return None
    return job.to_response()


def cancel_generation(job_id: str) -> bool:
    """Request cancellation of a running job.  Returns True if job found."""
    manager = get_job_manager()
    return manager.cancel_job(job_id)
