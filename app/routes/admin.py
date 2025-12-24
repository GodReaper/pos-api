from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.user import User, UserCreate
from app.models.assignment import Assignment, AssignmentCreate
from app.services.auth_service import create_biller
from app.services.assignment_service import (
    create_or_update_assignment_service,
    get_assignments
)
from app.repositories.user_repo import get_all_users
from app.core.rbac import require_admin, get_current_user

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

