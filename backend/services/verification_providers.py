"""
Email verification providers interface and implementations.

Supports:
  * TechnicalVerificationProvider (Free, offline/local DNS/MX checks)
  * HunterVerificationProvider (Hunter.io Email Verifier API)
  * ZeroBounceVerificationProvider (ZeroBounce API)
  * GenericVerificationProvider (Custom HTTP webhook/API)
"""

import abc
import os
from dataclasses import dataclass, field
from typing import Optional

import httpx

from utils.logging_config import logger


@dataclass
class ProviderVerificationResult:
    status: str  # VALID, INVALID, RISKY, UNKNOWN
    reason: str
    mailbox_confirmed: Optional[bool] = None
    is_catch_all: Optional[bool] = None
    is_disposable: Optional[bool] = None
    provider: str = "technical"
    raw_response: dict = field(default_factory=dict)


class EmailVerificationProvider(abc.ABC):
    """Abstract base class for email verification providers."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Provider identifier."""
        pass

    @abc.abstractmethod
    async def verify(
        self,
        email: str,
        local_part: str,
        domain: str,
        syntax_valid: bool,
        domain_exists: bool,
        has_mx: bool,
        mx_records: list[str],
        is_disposable: bool,
        is_catch_all: Optional[bool] = None,
    ) -> ProviderVerificationResult:
        """Verify the email using provider-specific logic."""
        pass


class TechnicalVerificationProvider(EmailVerificationProvider):
    """
    Local technical verification provider (free, requires no external paid API).

    Rules:
      * Syntax invalid -> INVALID
      * Domain doesn't exist / NXDOMAIN -> INVALID
      * No MX records found -> INVALID
      * Disposable temporary email -> RISKY
      * Catch-all detected -> RISKY
      * Valid syntax + valid MX + not disposable:
        Because an MX record proves only the mail host exists, NOT that the
        individual mailbox exists, technical verification alone cannot confirm
        mailbox existence without sending mail. Therefore, status is RISKY
        (high technical quality, mailbox unconfirmed).
    """

    @property
    def name(self) -> str:
        return "technical"

    async def verify(
        self,
        email: str,
        local_part: str,
        domain: str,
        syntax_valid: bool,
        domain_exists: bool,
        has_mx: bool,
        mx_records: list[str],
        is_disposable: bool,
        is_catch_all: Optional[bool] = None,
    ) -> ProviderVerificationResult:
        if not syntax_valid:
            return ProviderVerificationResult(
                status="INVALID",
                reason="Invalid email syntax format",
                mailbox_confirmed=False,
                is_disposable=is_disposable,
                is_catch_all=is_catch_all,
                provider=self.name,
            )

        if not domain_exists:
            return ProviderVerificationResult(
                status="INVALID",
                reason=f"Domain '{domain}' does not exist (DNS NXDOMAIN)",
                mailbox_confirmed=False,
                is_disposable=is_disposable,
                is_catch_all=is_catch_all,
                provider=self.name,
            )

        if not has_mx:
            return ProviderVerificationResult(
                status="INVALID",
                reason=f"Domain '{domain}' has no Mail Exchange (MX) records",
                mailbox_confirmed=False,
                is_disposable=is_disposable,
                is_catch_all=is_catch_all,
                provider=self.name,
            )

        if is_disposable:
            return ProviderVerificationResult(
                status="RISKY",
                reason=f"Domain '{domain}' is a temporary/disposable email service",
                mailbox_confirmed=None,
                is_disposable=True,
                is_catch_all=is_catch_all,
                provider=self.name,
            )

        if is_catch_all is True:
            return ProviderVerificationResult(
                status="RISKY",
                reason="Mail server is configured as catch-all (accepts all addresses)",
                mailbox_confirmed=None,
                is_disposable=False,
                is_catch_all=True,
                provider=self.name,
            )

        # Technical checks all passed (Syntax OK, Domain OK, MX OK, Not disposable).
        # Per prompt rules: An existing MX record does NOT prove that a specific mailbox exists.
        # Do not mark an email as fully verified based only on syntax or MX checks.
        primary_mx = mx_records[0] if mx_records else "mail server"
        return ProviderVerificationResult(
            status="RISKY",
            reason=f"Technical checks passed (MX: {primary_mx}), but mailbox unconfirmed without paid verification API",
            mailbox_confirmed=None,  # unconfirmed
            is_disposable=False,
            is_catch_all=is_catch_all,
            provider=self.name,
        )


class HunterVerificationProvider(EmailVerificationProvider):
    """
    Hunter.io Email Verifier API provider.
    https://hunter.io/api-documentation/v2#email-verifier
    """

    def __init__(self, api_key: str):
        self.api_key = api_key.strip()

    @property
    def name(self) -> str:
        return "hunter"

    async def verify(
        self,
        email: str,
        local_part: str,
        domain: str,
        syntax_valid: bool,
        domain_exists: bool,
        has_mx: bool,
        mx_records: list[str],
        is_disposable: bool,
        is_catch_all: Optional[bool] = None,
    ) -> ProviderVerificationResult:
        if not syntax_valid or not domain_exists or not has_mx:
            # Short-circuit invalid technical state
            return await TechnicalVerificationProvider().verify(
                email, local_part, domain, syntax_valid, domain_exists, has_mx, mx_records, is_disposable, is_catch_all
            )

        if not self.api_key:
            logger.warning("Hunter provider requested but no API key configured; falling back to technical")
            res = await TechnicalVerificationProvider().verify(
                email, local_part, domain, syntax_valid, domain_exists, has_mx, mx_records, is_disposable, is_catch_all
            )
            res.provider = "hunter_fallback_technical"
            return res

        url = "https://api.hunter.io/v2/email-verifier"
        params = {"email": email, "api_key": self.api_key}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json().get("data", {})
                    hunter_status = (data.get("status") or "").lower()
                    data_result = (data.get("result") or "").lower()
                    score = data.get("score", 0)

                    # Map hunter result
                    if data_result == "deliverable" or hunter_status == "valid":
                        return ProviderVerificationResult(
                            status="VALID",
                            reason=f"Hunter confirmed mailbox deliverable (score: {score})",
                            mailbox_confirmed=True,
                            is_catch_all=data.get("accept_all", False),
                            is_disposable=data.get("disposable", False),
                            provider=self.name,
                            raw_response=data,
                        )
                    elif data_result == "undeliverable" or hunter_status == "invalid":
                        return ProviderVerificationResult(
                            status="INVALID",
                            reason=f"Hunter reported mailbox undeliverable",
                            mailbox_confirmed=False,
                            is_catch_all=data.get("accept_all", False),
                            is_disposable=data.get("disposable", False),
                            provider=self.name,
                            raw_response=data,
                        )
                    elif data_result == "risky" or data.get("accept_all"):
                        return ProviderVerificationResult(
                            status="RISKY",
                            reason=f"Hunter reported mailbox as risky/accept-all (score: {score})",
                            mailbox_confirmed=None,
                            is_catch_all=True,
                            is_disposable=data.get("disposable", False),
                            provider=self.name,
                            raw_response=data,
                        )
                    else:
                        return ProviderVerificationResult(
                            status="UNKNOWN",
                            reason=f"Hunter verification result inconclusive ({hunter_status})",
                            mailbox_confirmed=None,
                            provider=self.name,
                            raw_response=data,
                        )
                elif resp.status_code == 429:
                    logger.warning("Hunter API rate limit exceeded")
                    return ProviderVerificationResult(
                        status="UNKNOWN",
                        reason="Hunter API rate limit reached",
                        provider=self.name,
                    )
                else:
                    logger.warning(f"Hunter API error: HTTP {resp.status_code}")
                    return ProviderVerificationResult(
                        status="UNKNOWN",
                        reason=f"Hunter API returned HTTP {resp.status_code}",
                        provider=self.name,
                    )
        except Exception as exc:
            logger.warning(f"Hunter verification exception: {exc}")
            return ProviderVerificationResult(
                status="UNKNOWN",
                reason=f"Hunter API connection error: {exc}",
                provider=self.name,
            )


class ZeroBounceVerificationProvider(EmailVerificationProvider):
    """
    ZeroBounce API provider.
    https://www.zerobounce.net/docs/email-validation-api-quickstart/
    """

    def __init__(self, api_key: str):
        self.api_key = api_key.strip()

    @property
    def name(self) -> str:
        return "zerobounce"

    async def verify(
        self,
        email: str,
        local_part: str,
        domain: str,
        syntax_valid: bool,
        domain_exists: bool,
        has_mx: bool,
        mx_records: list[str],
        is_disposable: bool,
        is_catch_all: Optional[bool] = None,
    ) -> ProviderVerificationResult:
        if not syntax_valid or not domain_exists or not has_mx:
            return await TechnicalVerificationProvider().verify(
                email, local_part, domain, syntax_valid, domain_exists, has_mx, mx_records, is_disposable, is_catch_all
            )

        if not self.api_key:
            logger.warning("ZeroBounce provider requested but no API key configured; falling back to technical")
            res = await TechnicalVerificationProvider().verify(
                email, local_part, domain, syntax_valid, domain_exists, has_mx, mx_records, is_disposable, is_catch_all
            )
            res.provider = "zerobounce_fallback_technical"
            return res

        url = "https://api.zerobounce.net/v2/validate"
        params = {"email": email, "api_key": self.api_key, "ip_address": ""}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    zb_status = (data.get("status") or "").lower()
                    sub_status = (data.get("sub_status") or "").lower()

                    if zb_status == "valid":
                        return ProviderVerificationResult(
                            status="VALID",
                            reason="ZeroBounce confirmed mailbox valid",
                            mailbox_confirmed=True,
                            is_catch_all=False,
                            is_disposable=False,
                            provider=self.name,
                            raw_response=data,
                        )
                    elif zb_status == "invalid":
                        return ProviderVerificationResult(
                            status="INVALID",
                            reason=f"ZeroBounce reported mailbox invalid ({sub_status or 'mailbox not found'})",
                            mailbox_confirmed=False,
                            is_disposable=data.get("disposable", False),
                            provider=self.name,
                            raw_response=data,
                        )
                    elif zb_status in ("catch-all", "spamtrap", "abuse", "do_not_mail"):
                        return ProviderVerificationResult(
                            status="RISKY",
                            reason=f"ZeroBounce flagged mailbox as {zb_status} ({sub_status})",
                            mailbox_confirmed=None,
                            is_catch_all=zb_status == "catch-all",
                            is_disposable=data.get("disposable", False),
                            provider=self.name,
                            raw_response=data,
                        )
                    else:
                        return ProviderVerificationResult(
                            status="UNKNOWN",
                            reason=f"ZeroBounce status: {zb_status} ({sub_status})",
                            mailbox_confirmed=None,
                            provider=self.name,
                            raw_response=data,
                        )
                else:
                    return ProviderVerificationResult(
                        status="UNKNOWN",
                        reason=f"ZeroBounce API error HTTP {resp.status_code}",
                        provider=self.name,
                    )
        except Exception as exc:
            return ProviderVerificationResult(
                status="UNKNOWN",
                reason=f"ZeroBounce API connection error: {exc}",
                provider=self.name,
            )


class GenericVerificationProvider(EmailVerificationProvider):
    """
    Configurable custom HTTP API verification provider.
    Allows integration with any custom email verification service or webhook.
    """

    def __init__(self, api_url: str, api_key: str = ""):
        self.api_url = api_url.strip()
        self.api_key = api_key.strip()

    @property
    def name(self) -> str:
        return "generic"

    async def verify(
        self,
        email: str,
        local_part: str,
        domain: str,
        syntax_valid: bool,
        domain_exists: bool,
        has_mx: bool,
        mx_records: list[str],
        is_disposable: bool,
        is_catch_all: Optional[bool] = None,
    ) -> ProviderVerificationResult:
        if not self.api_url:
            return await TechnicalVerificationProvider().verify(
                email, local_part, domain, syntax_valid, domain_exists, has_mx, mx_records, is_disposable, is_catch_all
            )

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            headers["X-Api-Key"] = self.api_key

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                payload = {
                    "email": email,
                    "domain": domain,
                    "syntax_valid": syntax_valid,
                    "has_mx": has_mx,
                }
                resp = await client.post(self.api_url, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    status = str(data.get("status", "UNKNOWN")).upper()
                    if status not in ("VALID", "INVALID", "RISKY", "UNKNOWN"):
                        status = "UNKNOWN"
                    reason = str(data.get("reason") or f"Generic API returned {status}")
                    return ProviderVerificationResult(
                        status=status,
                        reason=reason,
                        mailbox_confirmed=data.get("mailbox_confirmed"),
                        is_catch_all=data.get("is_catch_all"),
                        is_disposable=data.get("is_disposable"),
                        provider=self.name,
                        raw_response=data,
                    )
                else:
                    return ProviderVerificationResult(
                        status="UNKNOWN",
                        reason=f"Generic API returned HTTP {resp.status_code}",
                        provider=self.name,
                    )
        except Exception as exc:
            return ProviderVerificationResult(
                status="UNKNOWN",
                reason=f"Generic API request failed: {exc}",
                provider=self.name,
            )


def get_verification_provider(
    provider_name: str,
    api_key: Optional[str] = None,
    api_url: Optional[str] = None,
) -> EmailVerificationProvider:
    """Factory to retrieve an instance of the configured provider."""
    name = (provider_name or "technical").lower().strip()
    key = api_key or ""
    url = api_url or ""

    if name == "hunter":
        return HunterVerificationProvider(api_key=key)
    elif name == "zerobounce":
        return ZeroBounceVerificationProvider(api_key=key)
    elif name == "generic":
        return GenericVerificationProvider(api_url=url, api_key=key)
    else:
        return TechnicalVerificationProvider()
