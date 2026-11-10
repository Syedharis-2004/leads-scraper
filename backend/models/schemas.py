"""
Pydantic models / schemas for API request and response validation.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, HttpUrl, field_validator


# ---------------------------------------------------------------------------
# Lead
# ---------------------------------------------------------------------------
class Lead(BaseModel):
    """A single generated lead record."""
    lead_id: str
    company_name: str = ""
    owner_name: str = ""
    website: str = ""
    email: str = ""
    phone: str = ""
    city: str = ""
    country: str = ""
    business_type: str = ""
    description: str = ""
    source_url: str = ""
    search_query: str = ""
    generated_at: str = ""
    verification_status: str = ""  # VALID, INVALID, RISKY, UNKNOWN, or "" (Unverified)
    verification_reason: str = ""
    verification_details: str = ""
    verified_at: str = ""


class LeadListResponse(BaseModel):
    leads: list[Lead]
    total: int
    page: int
    page_size: int
    total_pages: int


class LeadDetailResponse(Lead):
    pass


# ---------------------------------------------------------------------------
# Settings / API key
# ---------------------------------------------------------------------------
class ApiKeyRequest(BaseModel):
    api_key: str = Field(..., min_length=10, description="Google AI Studio API key")

    @field_validator("api_key")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class ApiKeyStatusResponse(BaseModel):
    has_key: bool
    model: str
    available_models: list[str]


class ApiKeyTestResponse(BaseModel):
    valid: bool
    model: str
    message: str
    detail: str = ""


class ModelUpdateRequest(BaseModel):
    model: str


# ---------------------------------------------------------------------------
# Lead generation
# ---------------------------------------------------------------------------
class GenerationRequest(BaseModel):
    prompt: str = Field(..., min_length=5, max_length=2000,
                        description="Natural-language lead generation prompt")


class SearchConfig(BaseModel):
    """Structured search configuration produced by Gemini from the prompt."""
    business_type: str = ""
    location: str = ""
    limit: int = Field(default=25, ge=1, le=200)
    fields: list[str] = Field(default_factory=list)
    raw_prompt: str = ""


class GenerationStatusResponse(BaseModel):
    job_id: str
    stage: str = ""           # e.g. "parsing_prompt", "discovering", "scraping", "complete"
    message: str = ""
    total_websites: int = 0
    websites_discovered: int = 0
    websites_processed: int = 0
    leads_extracted: int = 0
    duplicates_skipped: int = 0
    failed_websites: int = 0
    failed_urls: list[str] = Field(default_factory=list)
    progress: float = 0.0     # 0–100
    is_running: bool = False
    is_completed: bool = False
    is_cancelled: bool = False
    error: str = ""
    search_config: Optional[SearchConfig] = None
    new_lead_ids: list[str] = Field(default_factory=list)


class GenerationStartResponse(BaseModel):
    job_id: str
    status: str = "started"


class CancelResponse(BaseModel):
    job_id: str
    cancelled: bool


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
class VerificationStatsResponse(BaseModel):
    total: int = 0
    verified: int = 0
    unverified: int = 0
    valid: int = 0
    invalid: int = 0
    risky: int = 0
    unknown: int = 0


class DashboardStats(BaseModel):
    total_leads: int = 0
    leads_today: int = 0
    total_searches: int = 0
    successful_searches: int = 0
    failed_searches: int = 0
    recent_leads: list[Lead] = Field(default_factory=list)
    verification_stats: Optional[VerificationStatsResponse] = None


# ---------------------------------------------------------------------------
# Verification Schemas
# ---------------------------------------------------------------------------
class VerificationCheckDetails(BaseModel):
    syntax_valid: bool = False
    domain_exists: bool = False
    has_mx: bool = False
    mx_records: list[str] = Field(default_factory=list)
    is_disposable: bool = False
    is_catch_all: Optional[bool] = None
    mailbox_confirmed: Optional[bool] = None
    provider: str = "technical"
    checked_at: str = ""


class SingleVerificationResponse(BaseModel):
    lead_id: str
    email: str
    status: str       # VALID, INVALID, RISKY, UNKNOWN
    reason: str
    details: VerificationCheckDetails
    verified_at: str


class BatchVerificationRequest(BaseModel):
    lead_ids: Optional[list[str]] = Field(default=None, description="Specific lead IDs to verify")
    verify_all_unverified: bool = Field(default=False, description="Verify all leads without verification status")
    reverify_all: bool = Field(default=False, description="Re-verify all leads regardless of existing status")


class BatchVerificationStartResponse(BaseModel):
    job_id: str
    total_leads: int
    status: str = "started"


class BatchVerificationStatusResponse(BaseModel):
    job_id: str
    total_leads: int = 0
    processed_leads: int = 0
    valid_count: int = 0
    invalid_count: int = 0
    risky_count: int = 0
    unknown_count: int = 0
    progress: float = 0.0
    is_running: bool = False
    is_completed: bool = False
    is_cancelled: bool = False
    error: str = ""
    message: str = ""


class VerificationSettingsRequest(BaseModel):
    provider: str = Field(..., description="Provider name: technical, hunter, zerobounce, generic")
    api_key: Optional[str] = Field(default=None, description="Optional API key for provider")
    api_url: Optional[str] = Field(default=None, description="Optional custom endpoint URL for generic provider")


class VerificationSettingsResponse(BaseModel):
    provider: str
    available_providers: list[str]
    has_api_key: bool
    api_url: str = ""


class ActivityEntry(BaseModel):
    timestamp: str
    level: str
    message: str


class ActivityLogResponse(BaseModel):
    entries: list[ActivityEntry]
    total: int


# ---------------------------------------------------------------------------
# Generic responses
# ---------------------------------------------------------------------------
class MessageResponse(BaseModel):
    message: str
    detail: str = ""


class ErrorResponse(BaseModel):
    error: str
    detail: str = ""
    code: str = ""


# ---------------------------------------------------------------------------
# Lead query params
# ---------------------------------------------------------------------------
class LeadQueryParams(BaseModel):
    search: str = ""
    city: str = ""
    business_type: str = ""
    date_from: str = ""
    date_to: str = ""
    sort_by: str = "generated_at"
    sort_order: str = "desc"  # asc | desc
    page: int = 1
    page_size: int = 50

    @field_validator("sort_by")
    @classmethod
    def _valid_sort(cls, v: str) -> str:
        allowed = {"generated_at", "company_name", "city", "business_type", "lead_id"}
        return v if v in allowed else "generated_at"

    @field_validator("sort_order")
    @classmethod
    def _valid_order(cls, v: str) -> str:
        return v if v in ("asc", "desc") else "desc"
