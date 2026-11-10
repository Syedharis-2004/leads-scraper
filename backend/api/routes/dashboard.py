"""
Dashboard statistics route.
"""

from fastapi import APIRouter

from models.schemas import DashboardStats, Lead, VerificationStatsResponse
from services.csv_service import (
    count_leads,
    count_leads_today,
    get_search_stats,
    get_verification_stats,
    query_leads,
)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def get_stats():
    """Return dashboard summary statistics."""
    total = count_leads()
    today = count_leads_today()
    total_searches, successful, failed = get_search_stats()
    v_stats = get_verification_stats()

    # Recent leads (latest 10)
    recent, _ = query_leads(
        sort_by="generated_at",
        sort_order="desc",
        page=1,
        page_size=10,
    )

    return DashboardStats(
        total_leads=total,
        leads_today=today,
        total_searches=total_searches,
        successful_searches=successful,
        failed_searches=failed,
        recent_leads=[Lead(**lead) for lead in recent],
        verification_stats=VerificationStatsResponse(**v_stats),
    )
