"""
Tests for the FastAPI API endpoints.

Uses the FastAPI TestClient (httpx-backed) to exercise every route
without starting a real server.
"""

import csv
import json

import pytest

from services import csv_service


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
def test_health(app_client):
    res = app_client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["service"] == "ai-lead-generator"


# ---------------------------------------------------------------------------
# Settings / API key
# ---------------------------------------------------------------------------
def test_key_status_no_key(app_client):
    res = app_client.get("/api/settings/key")
    assert res.status_code == 200
    data = res.json()
    assert data["has_key"] is False
    assert "available_models" in data
    assert len(data["available_models"]) > 0


def test_save_and_test_key(app_client, monkeypatch):
    # Mock the secure storage to accept our key
    monkeypatch.setattr("api.routes.settings.save_api_key", lambda k: None)
    monkeypatch.setattr("api.routes.settings.has_api_key", lambda: True)
    monkeypatch.setattr("api.routes.settings.get_api_key", lambda: "fake-key")

    # Save key
    res = app_client.post("/api/settings/key", json={"api_key": "AIza-test-key-1234567890"})
    assert res.status_code == 200

    # Key status should now show has_key=True
    res = app_client.get("/api/settings/key")
    assert res.json()["has_key"] is True

    # Test key with mocked validation
    from services.gemini_service import ApiKeyTestResponse
    monkeypatch.setattr(
        "api.routes.settings.validate_api_key",
        lambda api_key=None, model=None: ApiKeyTestResponse(
            valid=True, model="gemini-2.0-flash", message="API key is valid"
        ),
    )
    res = app_client.post("/api/settings/key/test", json={"api_key": "AIza-test-key-1234567890"})
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True


def test_remove_key(app_client, monkeypatch):
    monkeypatch.setattr("api.routes.settings.remove_api_key", lambda: True)
    res = app_client.delete("/api/settings/key")
    assert res.status_code == 200
    assert "removed" in res.json()["message"].lower()


def test_set_model(app_client):
    res = app_client.put("/api/settings/model", json={"model": "gemini-2.5-flash"})
    assert res.status_code == 200

    res = app_client.get("/api/settings/models")
    assert res.json()["selected"] == "gemini-2.5-flash"


def test_set_invalid_model(app_client):
    res = app_client.put("/api/settings/model", json={"model": "nonexistent-model"})
    assert res.status_code == 400


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
def test_dashboard_stats_empty(app_client):
    res = app_client.get("/api/dashboard/stats")
    assert res.status_code == 200
    data = res.json()
    assert data["total_leads"] == 0
    assert data["leads_today"] == 0
    assert data["recent_leads"] == []


def test_dashboard_stats_with_leads(app_client):
    csv_service.init_csv()
    csv_service.append_leads([
        {"company_name": "Test Corp", "website": "https://test.com", "city": "Karachi"},
    ])
    res = app_client.get("/api/dashboard/stats")
    assert res.status_code == 200
    data = res.json()
    assert data["total_leads"] == 1
    assert data["leads_today"] == 1
    assert len(data["recent_leads"]) == 1
    assert data["recent_leads"][0]["company_name"] == "Test Corp"


# ---------------------------------------------------------------------------
# Leads
# ---------------------------------------------------------------------------
def test_list_leads_empty(app_client):
    res = app_client.get("/api/leads")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 0
    assert data["leads"] == []


def test_list_leads_with_data(app_client):
    csv_service.init_csv()
    csv_service.append_leads([
        {"company_name": "Alpha", "city": "Karachi"},
        {"company_name": "Beta", "city": "Lahore"},
    ])
    res = app_client.get("/api/leads")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    assert len(data["leads"]) == 2


def test_get_single_lead(app_client):
    csv_service.init_csv()
    added, _ = csv_service.append_leads([{"company_name": "Alpha"}])
    lead_id = added[0]["lead_id"]

    res = app_client.get(f"/api/leads/{lead_id}")
    assert res.status_code == 200
    assert res.json()["company_name"] == "Alpha"


def test_get_lead_not_found(app_client):
    res = app_client.get("/api/leads/nonexistent-id")
    assert res.status_code == 404


def test_delete_lead(app_client):
    csv_service.init_csv()
    added, _ = csv_service.append_leads([{"company_name": "Alpha"}])
    lead_id = added[0]["lead_id"]

    res = app_client.delete(f"/api/leads/{lead_id}")
    assert res.status_code == 200
    assert len(csv_service.read_all_leads()) == 0


def test_delete_lead_not_found(app_client):
    res = app_client.delete("/api/leads/nonexistent")
    assert res.status_code == 404


def test_export_csv(app_client):
    csv_service.init_csv()
    csv_service.append_leads([{"company_name": "Export Test", "city": "Dubai"}])
    res = app_client.get("/api/leads/export/csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers.get("content-type", "")
    assert "Export Test" in res.text


def test_export_json(app_client):
    csv_service.init_csv()
    csv_service.append_leads([{"company_name": "JSON Test"}])
    res = app_client.get("/api/leads/export/json")
    assert res.status_code == 200
    assert "application/json" in res.headers.get("content-type", "")
    data = json.loads(res.text)
    assert any(l["company_name"] == "JSON Test" for l in data)


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------
def test_start_generation_no_key(app_client, monkeypatch):
    monkeypatch.setattr("api.routes.generation.has_api_key", lambda: False)
    res = app_client.post("/api/generation/start", json={"prompt": "Find businesses"})
    assert res.status_code == 400
    assert "API key" in res.json()["detail"]


def test_start_and_poll_generation(app_client, monkeypatch):
    """Test generation start + status polling with mocked pipeline."""
    monkeypatch.setattr("api.routes.generation.has_api_key", lambda: True)

    # Mock the lead service at the route module level (the route imports
    # these names directly, so we must patch where they are used).
    from services.lead_service import JobStatus
    mock_job = JobStatus("test-job-123")
    mock_job.stage = "complete"
    mock_job.is_running = False
    mock_job.is_completed = True
    mock_job.leads_extracted = 5
    mock_job.message = "Complete! 5 leads extracted."

    def mock_start(prompt):
        return "test-job-123"

    def mock_get_status(job_id):
        return mock_job.to_response()

    monkeypatch.setattr("api.routes.generation.start_generation", mock_start)
    monkeypatch.setattr("api.routes.generation.get_status", mock_get_status)

    # Start
    res = app_client.post("/api/generation/start", json={"prompt": "Find 10 cafes in London"})
    assert res.status_code == 200
    assert res.json()["job_id"] == "test-job-123"

    # Poll status
    res = app_client.get("/api/generation/status/test-job-123")
    assert res.status_code == 200
    data = res.json()
    assert data["is_completed"] is True
    assert data["leads_extracted"] == 5


def test_cancel_generation(app_client, monkeypatch):
    def mock_cancel(job_id):
        return True
    monkeypatch.setattr("api.routes.generation.cancel_generation", mock_cancel)
    res = app_client.post("/api/generation/cancel/test-job")
    assert res.status_code == 200
    assert res.json()["cancelled"] is True


def test_cancel_generation_not_found(app_client, monkeypatch):
    monkeypatch.setattr("api.routes.generation.cancel_generation", lambda jid: False)
    res = app_client.post("/api/generation/cancel/nonexistent")
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------------
def test_get_logs(app_client):
    res = app_client.get("/api/logs?lines=10")
    assert res.status_code == 200
    data = res.json()
    assert "entries" in data
    assert isinstance(data["entries"], list)


def test_get_logs_filtered(app_client):
    res = app_client.get("/api/logs?lines=100&level=INFO")
    assert res.status_code == 200
    data = res.json()
    for entry in data["entries"]:
        assert entry["level"] == "INFO"
