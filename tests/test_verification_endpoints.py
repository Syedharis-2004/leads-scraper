"""
End-to-end endpoint tests for Lead Verification and Settings.
"""

from unittest.mock import patch
import pytest

from services import csv_service


def test_verify_single_lead_endpoint(app_client, temp_data_dir):
    csv_service.init_csv()
    leads = [
        {"company_name": "Endpoint Co", "email": "contact@endpoint.com", "website": "https://endpoint.com"}
    ]
    added, _ = csv_service.append_leads(leads)
    lead_id = added[0]["lead_id"]

    with patch("services.verification_service.check_domain_dns_and_mx", return_value=(True, True, ["mx.endpoint.com"], "OK")):
        res = app_client.post(f"/api/verification/verify/{lead_id}")

    assert res.status_code == 200
    data = res.json()
    assert data["lead_id"] == lead_id
    assert data["status"] in ("VALID", "INVALID", "RISKY", "UNKNOWN")
    assert "details" in data
    assert data["details"]["has_mx"] is True


def test_verify_lead_not_found(app_client):
    res = app_client.post("/api/verification/verify/nonexistent-id")
    assert res.status_code == 404


def test_verify_raw_email_endpoint(app_client):
    res = app_client.post("/api/verification/verify-email?email=invalid..dot@bad.com")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "INVALID"
    assert "consecutive dots" in data["reason"].lower()


def test_batch_verification_endpoints(app_client, temp_data_dir):
    csv_service.init_csv()
    leads = [
        {"company_name": "Batch 1", "email": "b1@batch.com", "website": "https://batch1.com"},
        {"company_name": "Batch 2", "email": "b2@batch.com", "website": "https://batch2.com"},
    ]
    added, _ = csv_service.append_leads(leads)
    lead_ids = [l["lead_id"] for l in added]

    with patch("services.verification_service.check_domain_dns_and_mx", return_value=(True, True, ["mx.batch.com"], "OK")):
        res = app_client.post("/api/verification/verify-batch", json={"lead_ids": lead_ids})
        assert res.status_code == 200
        start_data = res.json()
        assert "job_id" in start_data
        job_id = start_data["job_id"]

        # Poll status
        status_res = app_client.get(f"/api/verification/status/{job_id}")
        assert status_res.status_code == 200
        status_data = status_res.json()
        assert status_data["job_id"] == job_id
        assert status_data["total_leads"] == 2


def test_verification_stats_endpoint(app_client, temp_data_dir):
    csv_service.init_csv()
    leads = [
        {"company_name": "Stats Co 1", "email": "s1@co.com", "website": "https://co1.com"},
        {"company_name": "Stats Co 2", "email": "s2@co.com", "website": "https://co2.com"},
    ]
    added, _ = csv_service.append_leads(leads)
    csv_service.update_lead(added[0]["lead_id"], {"verification_status": "VALID"})

    res = app_client.get("/api/verification/stats")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    assert data["verified"] == 1
    assert data["unverified"] == 1
    assert data["valid"] == 1


def test_leads_filter_by_verification_status(app_client, temp_data_dir):
    csv_service.init_csv()
    leads = [
        {"company_name": "Valid Co", "email": "v@co.com", "website": "https://co1.com"},
        {"company_name": "Invalid Co", "email": "i@co.com", "website": "https://co2.com"},
        {"company_name": "Unverified Co", "email": "u@co.com", "website": "https://co3.com"},
    ]
    added, _ = csv_service.append_leads(leads)
    csv_service.update_lead(added[0]["lead_id"], {"verification_status": "VALID"})
    csv_service.update_lead(added[1]["lead_id"], {"verification_status": "INVALID"})

    # Filter VALID
    res = app_client.get("/api/leads?verification_status=VALID")
    assert res.status_code == 200
    assert res.json()["total"] == 1
    assert res.json()["leads"][0]["company_name"] == "Valid Co"

    # Filter INVALID
    res = app_client.get("/api/leads?verification_status=INVALID")
    assert res.status_code == 200
    assert res.json()["total"] == 1
    assert res.json()["leads"][0]["company_name"] == "Invalid Co"

    # Filter UNVERIFIED
    res = app_client.get("/api/leads?verification_status=UNVERIFIED")
    assert res.status_code == 200
    assert res.json()["total"] == 1
    assert res.json()["leads"][0]["company_name"] == "Unverified Co"


def test_export_with_verification_filter(app_client, temp_data_dir):
    csv_service.init_csv()
    leads = [
        {"company_name": "Valid Co", "email": "v@co.com", "website": "https://co1.com"},
        {"company_name": "Invalid Co", "email": "i@co.com", "website": "https://co2.com"},
    ]
    added, _ = csv_service.append_leads(leads)
    csv_service.update_lead(added[0]["lead_id"], {"verification_status": "VALID"})
    csv_service.update_lead(added[1]["lead_id"], {"verification_status": "INVALID"})

    # Export CSV filtered
    res = app_client.get("/api/leads/export/csv?verification_status=VALID")
    assert res.status_code == 200
    assert "Valid Co" in res.text
    assert "Invalid Co" not in res.text


def test_verification_settings_endpoints(app_client):
    # GET settings
    res = app_client.get("/api/settings/verification")
    assert res.status_code == 200
    data = res.json()
    assert "provider" in data
    assert "available_providers" in data
    assert "technical" in data["available_providers"]

    # POST settings update
    res = app_client.post(
        "/api/settings/verification",
        json={"provider": "hunter", "api_key": "new-test-hunter-key"},
    )
    assert res.status_code == 200

    # Verify provider updated
    res = app_client.get("/api/settings/verification")
    assert res.json()["provider"] == "hunter"
    assert res.json()["has_api_key"] is True

    # Reset back to technical
    app_client.post(
        "/api/settings/verification",
        json={"provider": "technical"},
    )
