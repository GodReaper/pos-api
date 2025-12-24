from typing import List
import json
from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.models.user import User, UserCreate
from app.models.assignment import Assignment, AssignmentCreate
from app.services.auth_service import create_biller
from app.services.assignment_service import (
    create_or_update_assignment_service,
    get_assignments
)
from app.repositories.user_repo import get_all_users
from app.core.rbac import require_admin, get_current_user
from app.services.admin_reporting_service import (
    get_admin_summary,
    get_running_tables,
    get_biller_performance,
)
from app.db.redis import get_cache, set_cache

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=List[User], dependencies=[Depends(require_admin)])
async def list_users():
    """Get all users (admin only)"""
    return await get_all_users()


@router.post("/users", response_model=User, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new biller user (admin only)"""
    # Only allow creating biller users through this endpoint
    if user_data.role != "biller":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint can only create biller users"
        )
    
    return await create_biller(user_data.username, user_data.password)


@router.post("/assign", response_model=Assignment, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
async def assign_biller_to_areas(
    assignment_data: AssignmentCreate,
    current_user: User = Depends(get_current_user)
):
    """Assign a biller to area_ids (admin only)"""
    return await create_or_update_assignment_service(current_user.id, assignment_data)


@router.get("/assignments", response_model=List[Assignment], dependencies=[Depends(require_admin)])
async def list_assignments():
    """Get all assignments (admin only)"""
    return await get_assignments()


@router.get("/summary", dependencies=[Depends(require_admin)])
async def admin_summary(date: str = Query("today")):
    """Get admin summary for a given date (default: today)."""
    # Redis cache key (TTL: 60s)
    cache_key = f"admin:summary:{date}"
    cached = await get_cache(cache_key)
    if cached:
        try:
            return json.loads(cached)
        except Exception:
            pass

    data = await get_admin_summary(date)

    try:
        await set_cache(cache_key, json.dumps(data), ttl=60)
    except Exception:
        pass

    return data


@router.get("/running-tables", dependencies=[Depends(require_admin)])
async def admin_running_tables():
    """Get list of currently running tables with area, biller, and totals."""
    cache_key = "admin:running_tables"
    cached = await get_cache(cache_key)
    if cached:
        try:
            return json.loads(cached)
        except Exception:
            pass

    data = await get_running_tables()

    try:
        await set_cache(cache_key, json.dumps(data), ttl=60)
    except Exception:
        pass

    return data


@router.get("/biller-performance", dependencies=[Depends(require_admin)])
async def admin_biller_performance(date: str = Query("today")):
    """Get biller performance (totals per biller) for a given date (default: today)."""
    cache_key = f"admin:biller_performance:{date}"
    cached = await get_cache(cache_key)
    if cached:
        try:
            return json.loads(cached)
        except Exception:
            pass

    data = await get_biller_performance(date)

    try:
        await set_cache(cache_key, json.dumps(data), ttl=60)
    except Exception:
        pass

    return data

