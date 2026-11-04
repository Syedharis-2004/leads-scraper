"""
Tests for the lead generation pipeline orchestration.

All external services (Gemini, discovery, scraping) are mocked.
"""

import time
from unittest.mock import Mock, patch

import pytest

from services import lead_service
from services.lead_service import JobStatus, get_job_manager
from models.schemas import SearchConfig


def test_job_creation():
    """JobManager creates and retrieves jobs."""
    manager = get_job_manager()
    job = manager.create_job()
    assert job.job_id != ""
    assert manager.get_job(job.job_id) is not None


def test_job_cancel():
    """Cancelling a running job sets the cancel flag."""
    manager = get_job_manager()
    job = manager.create_job()
    job.is_running = True
    assert manager.cancel_job(job.job_id) is True
    assert job.cancelled is True


def test_job_cancel_not_running():
    """Cancelling a non-running job returns False."""
    manager = get_job_manager()
    job = manager.create_job()
    assert manager.cancel_job(job.job_id) is False


def test_job_status_response():
    """to_response produces a valid GenerationStatusResponse."""
    job = JobStatus("test-123")
    job.stage = "scraping"
    job.is_running = True
    job.total_websites = 10
    job.websites_processed = 3
    job.leads_extracted = 2

    resp = job.to_response()
    assert resp.job_id == "test-123"
    assert resp.stage == "scraping"
    assert resp.is_running is True
    assert resp.total_websites == 10
    assert resp.websites_processed == 3
    assert resp.leads_extracted == 2


def test_pipeline_no_api_key(temp_data_dir):
    """Pipeline reports error when no API key is configured."""
    with patch("services.lead_service.get_api_key", return_value=None):
        job = JobStatus("test-job")
        lead_service.run_generation_pipeline("Find businesses", job)

    assert job.is_completed is True
    assert job.is_running is False
    assert "API key" in job.error
    assert job.stage == "error"


def test_pipeline_prompt_parse_failure(temp_data_dir):
    """Pipeline handles Gemini prompt parsing failure."""
    from services.gemini_service import GeminiError

    with patch("services.lead_service.get_api_key", return_value="fake-key"):
        with patch("services.lead_service.parse_prompt", side_effect=GeminiError("Bad key")):
            job = JobStatus("test-job")
            lead_service.run_generation_pipeline("Find businesses", job)

    assert job.is_completed is True
    assert job.stage == "error"
    assert "Bad key" in job.error


def test_pipeline_no_results(temp_data_dir):
    """Pipeline reports error when discovery finds no URLs."""
    config = SearchConfig(business_type="Cafe", location="Mars", limit=5)

    with patch("services.lead_service.get_api_key", return_value="fake-key"):
        with patch("services.lead_service.parse_prompt", return_value=config):
            with patch("services.lead_service.discovery_service.search_businesses", return_value=[]):
                job = JobStatus("test-job")
                lead_service.run_generation_pipeline("Find cafes on Mars", job)

    assert job.is_completed is True
    assert job.stage == "error"
    assert "No businesses found" in job.error


def test_pipeline_success(temp_data_dir):
    """Full pipeline with mocked services produces leads."""
    config = SearchConfig(business_type="Cafe", location="London", limit=2)

    discovered = [
        {"url": "https://cafe1.com", "title": "Cafe 1", "description": "Great cafe"},
        {"url": "https://cafe2.com", "title": "Cafe 2", "description": "Nice cafe"},
    ]

    scraped_leads = [
        {"company_name": "Cafe One", "website": "https://cafe1.com", "email": "info@cafe1.com",
         "phone": "123", "city": "London"},
        {"company_name": "Cafe Two", "website": "https://cafe2.com", "email": "info@cafe2.com",
         "phone": "456", "city": "London"},
    ]

    def mock_scrape_batch(urls, config, model, api_key, on_progress=None, should_cancel=None):
        for i, url in enumerate(urls):
            if on_progress:
                on_progress(i + 1, len(urls), scraped_leads[i] if i < len(scraped_leads) else None, None)
        return scraped_leads[:len(urls)], []

    with patch("services.lead_service.get_api_key", return_value="fake-key"):
        with patch("services.lead_service.parse_prompt", return_value=config):
            with patch("services.lead_service.discovery_service.search_businesses", return_value=discovered):
                with patch("services.lead_service.scraping_service.scrape_batch", side_effect=mock_scrape_batch):
                    job = JobStatus("test-job")
                    lead_service.run_generation_pipeline("Find 2 cafes in London", job)

    assert job.is_completed is True
    assert job.stage == "complete"
    assert job.leads_extracted == 2
    assert job.failed_websites == 0
    assert job.progress == 100.0
    assert len(job.new_lead_ids) == 2

    # Verify leads were written to CSV
    from services import csv_service
    all_leads = csv_service.read_all_leads()
    assert len(all_leads) == 2


def test_pipeline_cancellation(temp_data_dir):
    """Pipeline respects cancellation request."""
    config = SearchConfig(business_type="Cafe", location="London", limit=5)
    discovered = [{"url": f"https://cafe{i}.com", "title": f"Cafe {i}", "description": ""} for i in range(5)]

    def mock_scrape_batch(urls, config, model, api_key, on_progress=None, should_cancel=None):
        # Simulate cancellation after 2 URLs
        for i, url in enumerate(urls):
            if should_cancel and should_cancel():
                break
            if on_progress:
                on_progress(i + 1, len(urls), {"company_name": f"Cafe {i}"}, None)
            if i >= 1:
                # Trigger cancellation for next iteration
                pass
        return [], []

    with patch("services.lead_service.get_api_key", return_value="fake-key"):
        with patch("services.lead_service.parse_prompt", return_value=config):
            with patch("services.lead_service.discovery_service.search_businesses", return_value=discovered):
                with patch("services.lead_service.scraping_service.scrape_batch", side_effect=mock_scrape_batch):
                    job = JobStatus("test-job")
                    job.cancel()
                    lead_service.run_generation_pipeline("Find cafes", job)

    assert job.is_cancelled is True
    assert job.is_completed is True


def test_normalise_lead():
    """Lead normalisation maps field name variants to canonical names."""
    raw = {
        "Company Name": "Test Corp",
        "Owner": "John Doe",
        "URL": "https://test.com",
        "Email": "info@test.com",
        "Phone Number": "555-1234",
        "City": "London",
        "Business Description": "A test company",
    }
    config = SearchConfig(business_type="Test", location="London", limit=1)
    lead = lead_service._normalise_lead(raw, config)
    assert lead is not None
    assert lead["company_name"] == "Test Corp"
    assert lead["owner_name"] == "John Doe"
    assert lead["website"] == "https://test.com"
    assert lead["email"] == "info@test.com"
    assert lead["phone"] == "555-1234"
    assert lead["city"] == "London"
    assert lead["description"] == "A test company"
    assert lead["business_type"] == "Test"


def test_normalise_lead_empty():
    """A lead with no useful data returns None."""
    raw = {"company_name": "", "website": "", "email": ""}
    config = SearchConfig(business_type="Test", location="", limit=1)
    lead = lead_service._normalise_lead(raw, config)
    assert lead is None


def test_normalise_lead_invalid_email():
    """Invalid emails are cleared."""
    raw = {"company_name": "Test", "email": "not-an-email"}
    config = SearchConfig(business_type="Test", location="", limit=1)
    lead = lead_service._normalise_lead(raw, config)
    assert lead["email"] == ""


def test_normalise_lead_website_protocol():
    """Websites without protocol get https:// prepended."""
    raw = {"company_name": "Test", "website": "test.com"}
    config = SearchConfig(business_type="Test", location="", limit=1)
    lead = lead_service._normalise_lead(raw, config)
    assert lead["website"] == "https://test.com"
