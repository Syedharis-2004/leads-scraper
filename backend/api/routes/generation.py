"""
Lead generation routes: start, status, cancel.
"""

from fastapi import APIRouter, HTTPException

from models.schemas import (
    CancelResponse,
    GenerationRequest,
    GenerationStartResponse,
    GenerationStatusResponse,
)
from services.lead_service import (
    cancel_generation,
    get_status,
    start_generation,
)
from utils.logging_config import logger
from utils.secure_storage import has_api_key

router = APIRouter(prefix="/api/generation", tags=["generation"])


@router.post("/start", response_model=GenerationStartResponse)
def start(req: GenerationRequest):
    """Start a new lead generation job."""
    if not has_api_key():
        raise HTTPException(
            status_code=400,
            detail="No API key configured. Please add your Gemini API key in Settings first.",
        )
    job_id = start_generation(req.prompt)
    logger.info(f"Generation started: job={job_id}, prompt={req.prompt[:80]}")
    return GenerationStartResponse(job_id=job_id, status="started")


@router.get("/status/{job_id}", response_model=GenerationStatusResponse)
def status(job_id: str):
    """Poll the status of a generation job."""
    result = get_status(job_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return result


@router.post("/cancel/{job_id}", response_model=CancelResponse)
def cancel(job_id: str):
    """Request cancellation of a running generation job."""
    cancelled = cancel_generation(job_id)
    if not cancelled:
        raise HTTPException(
            status_code=404,
            detail="Job not found or not running",
        )
    return CancelResponse(job_id=job_id, cancelled=True)
