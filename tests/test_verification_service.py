"""
Comprehensive unit and integration tests for Lead Verification service and providers.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from models.schemas import VerificationCheckDetails
from services import csv_service
from services.verification_providers import (
    GenericVerificationProvider,
    HunterVerificationProvider,
    ProviderVerificationResult,
    TechnicalVerificationProvider,
    ZeroBounceVerificationProvider,
    get_verification_provider,
)
from services.verification_service import (
    check_disposable_domain,
    check_domain_dns_and_mx,
    validate_email_syntax,
    verify_email_address,
    verify_single_lead,
    VerificationJobManager,
)


# ---------------------------------------------------------------------------
# Syntax Validation Tests
# ---------------------------------------------------------------------------

def test_syntax_valid_emails():
    valid_emails = [
        "john.doe@example.com",
        "sarah+leads@domain.co.uk",
        "first.last@sub.domain.org",
        "user_name-123@company.io",
        "contact@business.net",
    ]
    for email in valid_emails:
        ok, reason, local, domain = validate_email_syntax(email)
        assert ok is True, f"Expected {email} to be valid: {reason}"
        assert domain != ""
        assert local != ""


def test_syntax_invalid_emails():
    invalid_cases = [
        ("", "Email address is empty"),
        ("not-an-email", "Email is missing '@' separator"),
        ("@domain.com", "Email local part is empty"),
        ("user@", "Email domain part is empty"),
        ("user@domain", "Domain must contain at least one dot separating name and TLD"),
        ("user..name@domain.com", "Email contains consecutive dots"),
        ("user@domain..com", "Email contains consecutive dots"),
        ("user@-domain.com", "cannot start or end with a hyphen"),
        ("user@domain-.com", "cannot start or end with a hyphen"),
        ("user@domain.c", "Top-level domain 'c' is invalid"),
        ("a" * 65 + "@domain.com", "Email username exceeds 64 characters"),
    ]
    for email, expected_fragment in invalid_cases:
        ok, reason, _, _ = validate_email_syntax(email)
        assert ok is False, f"Expected {email} to be invalid"
        assert expected_fragment.lower() in reason.lower()


# ---------------------------------------------------------------------------
# Disposable Domain Tests
# ---------------------------------------------------------------------------

def test_disposable_domain_detection():
    disposable_samples = [
        "mailinator.com",
        "tempmail.com",
        "subdomain.mailinator.com",
        "guerrillamail.com",
        "10minutemail.net",
        "sharklasers.com",
        "yopmail.fr",
    ]
    for domain in disposable_samples:
        assert check_disposable_domain(domain) is True, f"Expected {domain} to be disposable"

    clean_samples = [
        "google.com",
        "microsoft.com",
        "apple.com",
        "mycompany.io",
        "harvard.edu",
    ]
    for domain in clean_samples:
        assert check_disposable_domain(domain) is False, f"Expected {domain} to not be disposable"


# ---------------------------------------------------------------------------
# DNS & MX Resolver Tests
# ---------------------------------------------------------------------------

def test_dns_mx_resolution_mocked():
    # Test when MX exists
    with patch("services.verification_service._DNS_AVAILABLE", True):
        mock_resolver = MagicMock()
        mock_rdata = MagicMock()
        mock_rdata.exchange = "mail.example.com."
        mock_rdata.preference = 10
        mock_resolver.resolve.return_value = [mock_rdata]

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            exists, has_mx, hosts, msg = check_domain_dns_and_mx("example.com")
            assert exists is True
            assert has_mx is True
            assert hosts == ["mail.example.com"]


def test_dns_nxdomain_mocked():
    import dns.resolver
    with patch("services.verification_service._DNS_AVAILABLE", True):
        mock_resolver = MagicMock()
        mock_resolver.resolve.side_effect = dns.resolver.NXDOMAIN()

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            exists, has_mx, hosts, msg = check_domain_dns_and_mx("nonexistent-domain-xyz123.com")
            assert exists is False
            assert has_mx is False
            assert "NXDOMAIN" in msg


def test_dns_no_mx_fallback_a_record():
    import dns.resolver
    with patch("services.verification_service._DNS_AVAILABLE", True):
        mock_resolver = MagicMock()

        def side_effect(domain, rdtype):
            if rdtype == "MX":
                raise dns.resolver.NoAnswer()
            elif rdtype == "A":
                return [MagicMock()]
            raise dns.resolver.NXDOMAIN()

        mock_resolver.resolve.side_effect = side_effect

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            exists, has_mx, hosts, msg = check_domain_dns_and_mx("nomx-domain.com")
            assert exists is True
            assert has_mx is False
            assert "has no MX records" in msg


def test_dns_timeout_handling():
    import dns.exception
    with patch("services.verification_service._DNS_AVAILABLE", True):
        mock_resolver = MagicMock()
        mock_resolver.resolve.side_effect = dns.exception.Timeout()

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            exists, has_mx, hosts, msg = check_domain_dns_and_mx("timeout-domain.com")
            assert exists is False
            assert has_mx is False
            assert "timed out" in msg


# ---------------------------------------------------------------------------
# Technical Provider Classification Rules
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_technical_verification_rules():
    provider = TechnicalVerificationProvider()

    # Rule 1: Syntax invalid -> INVALID
    res = await provider.verify(
        email="bad-email",
        local_part="",
        domain="",
        syntax_valid=False,
        domain_exists=False,
        has_mx=False,
        mx_records=[],
        is_disposable=False,
    )
    assert res.status == "INVALID"
    assert "syntax" in res.reason.lower()

    # Rule 2: Domain does not exist -> INVALID
    res = await provider.verify(
        email="user@nxdomain.com",
        local_part="user",
        domain="nxdomain.com",
        syntax_valid=True,
        domain_exists=False,
        has_mx=False,
        mx_records=[],
        is_disposable=False,
    )
    assert res.status == "INVALID"
    assert "does not exist" in res.reason.lower()

    # Rule 3: Missing MX -> INVALID
    res = await provider.verify(
        email="user@nomx.com",
        local_part="user",
        domain="nomx.com",
        syntax_valid=True,
        domain_exists=True,
        has_mx=False,
        mx_records=[],
        is_disposable=False,
    )
    assert res.status == "INVALID"
    assert "no mail exchange" in res.reason.lower()

    # Rule 4: Disposable -> RISKY
    res = await provider.verify(
        email="user@tempmail.com",
        local_part="user",
        domain="tempmail.com",
        syntax_valid=True,
        domain_exists=True,
        has_mx=True,
        mx_records=["mail.tempmail.com"],
        is_disposable=True,
    )
    assert res.status == "RISKY"
    assert "disposable" in res.reason.lower()

    # Rule 5: Catch-all -> RISKY
    res = await provider.verify(
        email="user@catchall.com",
        local_part="user",
        domain="catchall.com",
        syntax_valid=True,
        domain_exists=True,
        has_mx=True,
        mx_records=["mail.catchall.com"],
        is_disposable=False,
        is_catch_all=True,
    )
    assert res.status == "RISKY"
    assert "catch-all" in res.reason.lower()

    # Rule 6: MX exists + syntax ok + not disposable:
    # An MX record does NOT prove mailbox existence -> status is RISKY (mailbox unconfirmed)
    res = await provider.verify(
        email="user@company.com",
        local_part="user",
        domain="company.com",
        syntax_valid=True,
        domain_exists=True,
        has_mx=True,
        mx_records=["mail.company.com"],
        is_disposable=False,
    )
    assert res.status == "RISKY"
    assert "mailbox unconfirmed" in res.reason.lower()
    assert res.mailbox_confirmed is None


# ---------------------------------------------------------------------------
# Third-Party Provider Tests (Hunter & ZeroBounce & Generic)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hunter_provider_success():
    provider = HunterVerificationProvider(api_key="hunter-test-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": {
            "status": "valid",
            "result": "deliverable",
            "score": 98,
            "accept_all": False,
            "disposable": False,
        }
    }

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        res = await provider.verify(
            email="ceo@acme.com",
            local_part="ceo",
            domain="acme.com",
            syntax_valid=True,
            domain_exists=True,
            has_mx=True,
            mx_records=["mail.acme.com"],
            is_disposable=False,
        )
        assert res.status == "VALID"
        assert res.mailbox_confirmed is True
        assert "Hunter confirmed" in res.reason


@pytest.mark.asyncio
async def test_zerobounce_provider_invalid():
    provider = ZeroBounceVerificationProvider(api_key="zb-test-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "status": "invalid",
        "sub_status": "mailbox_not_found",
        "disposable": False,
    }

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        res = await provider.verify(
            email="nonexistent@acme.com",
            local_part="nonexistent",
            domain="acme.com",
            syntax_valid=True,
            domain_exists=True,
            has_mx=True,
            mx_records=["mail.acme.com"],
            is_disposable=False,
        )
        assert res.status == "INVALID"
        assert res.mailbox_confirmed is False


@pytest.mark.asyncio
async def test_generic_provider_api_error_fallback():
    provider = GenericVerificationProvider(api_url="https://api.custom-verify.com/check")

    with patch("httpx.AsyncClient.post", side_effect=Exception("Connection refused")):
        res = await provider.verify(
            email="test@custom.com",
            local_part="test",
            domain="custom.com",
            syntax_valid=True,
            domain_exists=True,
            has_mx=True,
            mx_records=["mail.custom.com"],
            is_disposable=False,
        )
        assert res.status == "UNKNOWN"
        assert "connection error" in res.reason.lower() or "failed" in res.reason.lower()


# ---------------------------------------------------------------------------
# Lead Verification and Persistence Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_verify_single_lead_persists(temp_data_dir):
    csv_service.init_csv()
    leads = [
        {"company_name": "Test Co", "email": "info@valid-test.com", "website": "https://valid-test.com"},
    ]
    added, _ = csv_service.append_leads(leads)
    lead_id = added[0]["lead_id"]

    # Mock DNS lookup to return valid MX
    with patch("services.verification_service.check_domain_dns_and_mx", return_value=(True, True, ["mx.test.com"], "OK")):
        res = await verify_single_lead(lead_id)

    assert res.lead_id == lead_id
    assert res.status == "RISKY"  # Technical mode: MX passes, mailbox unconfirmed
    assert res.verified_at != ""

    # Check persistence in CSV without losing original data
    lead_in_csv = csv_service.read_lead(lead_id)
    assert lead_in_csv is not None
    assert lead_in_csv["company_name"] == "Test Co"
    assert lead_in_csv["email"] == "info@valid-test.com"
    assert lead_in_csv["verification_status"] == "RISKY"
    assert lead_in_csv["verified_at"] == res.verified_at


# ---------------------------------------------------------------------------
# Batch Verification Job Manager Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_batch_verification_flow(temp_data_dir):
    csv_service.init_csv()
    leads = [
        {"company_name": "Bad Email Co", "email": "invalid@@syntax", "website": "https://bad.com"},
        {"company_name": "Good Co", "email": "hello@good.com", "website": "https://good.com"},
    ]
    added, _ = csv_service.append_leads(leads)
    lead_ids = [l["lead_id"] for l in added]

    manager = VerificationJobManager.get()

    with patch("services.verification_service.check_domain_dns_and_mx", return_value=(True, True, ["mx.good.com"], "OK")):
        job = await manager.start_batch_verification(lead_ids=lead_ids)
        assert job.job_id.startswith("VJ-")
        assert job.total_leads == 2

        # Wait for worker to finish
        for _ in range(50):
            if job.is_completed:
                break
            await asyncio.sleep(0.05)

        assert job.is_completed is True
        assert job.processed_leads == 2
        assert job.invalid_count == 1  # invalid@@syntax
        assert job.risky_count == 1    # hello@good.com (technical passed)


@pytest.mark.asyncio
async def test_batch_verification_cancellation(temp_data_dir):
    csv_service.init_csv()
    leads = [
        {"company_name": f"Co {i}", "email": f"test{i}@example.com", "website": f"https://example{i}.com"}
        for i in range(10)
    ]
    added, _ = csv_service.append_leads(leads)
    lead_ids = [l["lead_id"] for l in added]

    manager = VerificationJobManager.get()

    with patch("services.verification_service.check_domain_dns_and_mx", return_value=(True, True, ["mx.example.com"], "OK")):
        job = await manager.start_batch_verification(lead_ids=lead_ids)
        await asyncio.sleep(0.02)
        cancelled = await manager.cancel_job(job.job_id)
        assert cancelled is True
        await asyncio.sleep(0.1)
        assert job.is_cancelled is True
