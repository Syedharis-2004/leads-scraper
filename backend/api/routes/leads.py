"""
Leads CRUD, search, filter, sort, export routes.
"""

import csv
import io
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from models.schemas import Lead, LeadListResponse, MessageResponse
from services.csv_service import delete_lead, query_leads, read_lead
from utils.logging_config import logger

router = APIRouter(prefix="/api/leads", tags=["leads"])


# ---------------------------------------------------------------------------
# List / search / filter / sort / paginate
# ---------------------------------------------------------------------------
@router.get("", response_model=LeadListResponse)
def list_leads(
    search: str = Query("", description="Search by company name"),
    city: str = Query("", description="Filter by city"),
    business_type: str = Query("", description="Filter by business type"),
    verification_status: str = Query("", description="Filter by status: VALID, INVALID, RISKY, UNKNOWN, UNVERIFIED"),
    date_from: str = Query("", description="Date from (YYYY-MM-DD)"),
    date_to: str = Query("", description="Date to (YYYY-MM-DD)"),
    sort_by: str = Query("generated_at", description="Sort field"),
    sort_order: str = Query("desc", description="asc or desc"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
):
    """List leads with search, filter, sort, and pagination."""
    leads, total = query_leads(
        search=search,
        city=city,
        business_type=business_type,
        verification_status=verification_status,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )

    total_pages = (total + page_size - 1) // page_size if total else 0

    return LeadListResponse(
        leads=[Lead(**lead) for lead in leads],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# ---------------------------------------------------------------------------
# Single lead
# ---------------------------------------------------------------------------
@router.get("/{lead_id}", response_model=Lead)
def get_lead(lead_id: str):
    """Get a single lead by ID."""
    lead = read_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return Lead(**lead)


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------
@router.delete("/{lead_id}", response_model=MessageResponse)
def remove_lead(lead_id: str):
    """Delete a single lead by ID."""
    deleted = delete_lead(lead_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Lead not found")
    logger.info(f"Lead deleted: {lead_id}")
    return MessageResponse(message="Lead deleted successfully")


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
@router.get("/export/csv")
def export_csv(
    search: str = Query(""),
    city: str = Query(""),
    business_type: str = Query(""),
    verification_status: str = Query(""),
    date_from: str = Query(""),
    date_to: str = Query(""),
):
    """Export filtered leads as CSV."""
    from services.csv_service import export_csv as do_export

    csv_content = do_export(
        search=search,
        city=city,
        business_type=business_type,
        verification_status=verification_status,
        date_from=date_from,
        date_to=date_to,
    )
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"leads_export_{timestamp}.csv"
    if verification_status:
        filename = f"leads_{verification_status.lower()}_{timestamp}.csv"

    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"'
    }
    return StreamingResponse(
        io.BytesIO(csv_content.encode("utf-8-sig")),
        media_type="text/csv",
        headers=headers,
    )


@router.get("/export/json")
def export_json(
    search: str = Query(""),
    city: str = Query(""),
    business_type: str = Query(""),
    verification_status: str = Query(""),
    date_from: str = Query(""),
    date_to: str = Query(""),
):
    """Export filtered leads as JSON."""
    from services.csv_service import export_json as do_export

    json_content = do_export(
        search=search,
        city=city,
        business_type=business_type,
        verification_status=verification_status,
        date_from=date_from,
        date_to=date_to,
    )
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"leads_export_{timestamp}.json"
    if verification_status:
        filename = f"leads_{verification_status.lower()}_{timestamp}.json"

    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"'
    }
    return StreamingResponse(
        io.BytesIO(json_content.encode("utf-8")),
        media_type="application/json",
        headers=headers,
    )
