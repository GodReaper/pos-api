import json
from fastapi import APIRouter, Query
from app.services.reports_service import get_reports_by_username
from app.db.redis import get_cache, set_cache

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/{username}")
async def get_reports(
    username: str,
    date: str = Query("today", description="Date filter (default: 'today', or YYYY-MM-DD format)")
):
    """
    Get reports for a specific username.
    
    - **username**: The username to get reports for
    - **date**: Date filter (default: 'today', or YYYY-MM-DD format)
    
    Returns admin-style reports (summary, running tables, biller performance) 
    filtered by the specified username.
    
    This endpoint is publicly accessible - anyone who knows the username can view the reports.
    """
    # Check cache
    cache_key = f"reports:{username}:{date}"
    cached = await get_cache(cache_key)
    if cached:
        try:
            return json.loads(cached)
        except Exception:
            pass

    data = await get_reports_by_username(username, date)

    try:
        await set_cache(cache_key, json.dumps(data), ttl=60)
    except Exception:
        pass

    return data

