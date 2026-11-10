"""
Lead verification API routes.
"""

from fastapi import APIRouter, HTTPException, Query

from models.schemas import (
    BatchVerificationRequest,
    BatchVerificationStartResponse,
    BatchVerificationStatusResponse,
    CancelResponse,
    MessageResponse,
    SingleVerificationResponse,
    VerificationCheckDetails,
    VerificationStatsResponse,
)
from services import csv_service
from services.verification_service import (
    VerificationJobManager,
    verify_email_address,
    verify_single_lead,
)
from utils.logging_config import logger

router = APIRouter(prefix="/api/verification", tags=["verification"])


@router.post("/verify/{lead_id}", response_model=SingleVerificationResponse)
async def verify_lead(lead_id: str, provider: str = Query("", description="Optional provider override")):
    """Verify an individual lead by ID."""
    try:
        return await verify_single_lead(lead_id=lead_id, provider_name=provider or None)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception(f"Verification error for lead {lead_id}: {exc}")
        raise HTTPException(status_code=500, detail=f"Verification failed: {exc}")


@router.post("/verify-batch", response_model=BatchVerificationStartResponse)
async def start_batch_verification(req: BatchVerificationRequest):
    """Start a background verification job for multiple leads."""
    manager = VerificationJobManager.get()
    try:
        job = await manager.start_batch_verification(
            lead_ids=req.lead_ids,
            verify_all_unverified=req.verify_all_unverified,
            reverify_all=req.reverify_all,
        )
        return BatchVerificationStartResponse(job_id=job.job_id, total_leads=job.total_leads)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception(f"Failed to start batch verification: {exc}")
        raise HTTPException(status_code=500, detail=f"Batch verification error: {exc}")


@router.get("/status/{job_id}", response_model=BatchVerificationStatusResponse)
def get_batch_status(job_id: str):
    """Retrieve the progress and status of a verification job."""
    manager = VerificationJobManager.get()
    job = manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Verification job not found")
    return job.to_status_response()


@router.get("/active", response_model=BatchVerificationStatusResponse | None)
def get_active_batch_job():
    """Get the currently running batch verification job, if any."""
    manager = VerificationJobManager.get()
    active_job = manager.get_active_job()
    if active_job:
        return active_job.to_status_response()
    return None


@router.post("/cancel/{job_id}", response_model=CancelResponse)
async def cancel_batch_verification(job_id: str):
    """Cancel an active batch verification job."""
    manager = VerificationJobManager.get()
    cancelled = await manager.cancel_job(job_id)
    if not cancelled:
        raise HTTPException(status_code=400, detail="Job is not currently running or not found")
    return CancelResponse(job_id=job_id, cancelled=True)


@router.get("/stats", response_model=VerificationStatsResponse)
def get_stats():
    """Retrieve lead verification summary statistics."""
    stats = csv_service.get_verification_stats()
    return VerificationStatsResponse(**stats)


@router.post("/verify-email", response_model=SingleVerificationResponse)
async def verify_raw_email(
    email: str = Query(..., description="Email address to verify"),
    provider: str = Query("", description="Optional provider override"),
):
    """Verify an arbitrary email on the fly (syntax, MX, DNS, disposable, provider)."""
    status, reason, details = await verify_email_address(email, provider_name=provider or None)
    return SingleVerificationResponse(
        lead_id="test",
        email=email,
        status=status,
        reason=reason,
        details=details,
        verified_at=details.checked_at,
    )
