from typing import List, Optional
from fastapi import HTTPException, status
from app.models.assignment import AssignmentCreate, AssignmentUpdate, Assignment, AssignmentInDB
from app.repositories.assignment_repo import (
    get_assignment_by_biller_id,
    get_all_assignments,
    create_or_update_assignment,
    delete_assignment_by_biller_id,
    assignment_exists_for_biller,
    get_assigned_area_ids_for_biller
)
from app.repositories.user_repo import get_user_by_id
from app.repositories.area_repo import area_exists


async def get_assignments() -> List[Assignment]:
    """Get all assignments"""
    return await get_all_assignments()


async def get_assignment(biller_id: str) -> Optional[Assignment]:
    """Get assignment for a biller"""
    return await get_assignment_by_biller_id(biller_id)


async def create_or_update_assignment_service(
    admin_id: str,
    assignment_data: AssignmentCreate
) -> Assignment:
    """Create or update an assignment"""
    # Verify biller exists and is a biller
    biller = await get_user_by_id(assignment_data.biller_id)
    if not biller:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Biller user not found"
        )
    
    if biller.role != "biller":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a biller"
        )
    
    # Verify all area_ids exist
    for area_id in assignment_data.area_ids:
        if not await area_exists(area_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Area {area_id} not found"
            )
    
    # Override admin_id from current user
    assignment_dict = assignment_data.model_dump()
    assignment_dict["admin_id"] = admin_id
    
    assignment_in_db = AssignmentInDB(**assignment_dict)
    return await create_or_update_assignment(assignment_in_db)


async def update_assignment_service(
    biller_id: str,
    assignment_data: AssignmentUpdate
) -> Assignment:
    """Update an assignment"""
    if not await assignment_exists_for_biller(biller_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found for this biller"
        )
    
    # Verify all area_ids exist
    for area_id in assignment_data.area_ids:
        if not await area_exists(area_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Area {area_id} not found"
            )
    
    # Get existing assignment to preserve admin_id
    existing = await get_assignment_by_biller_id(biller_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )
    
    assignment_dict = assignment_data.model_dump()
    assignment_dict["admin_id"] = existing.admin_id
    assignment_dict["biller_id"] = biller_id
    
    assignment_in_db = AssignmentInDB(**assignment_dict)
    return await create_or_update_assignment(assignment_in_db)


async def delete_assignment_service(biller_id: str) -> bool:
    """Delete an assignment"""
    if not await assignment_exists_for_biller(biller_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found for this biller"
        )
    
    return await delete_assignment_by_biller_id(biller_id)


async def get_assigned_areas_for_biller(biller_id: str) -> List[str]:
    """Get list of area IDs assigned to a biller"""
    return await get_assigned_area_ids_for_biller(biller_id)


async def is_biller_assigned_to_area(biller_id: str, area_id: str) -> bool:
    """Check if a biller is assigned to an area"""
    assigned_area_ids = await get_assigned_area_ids_for_biller(biller_id)
    return area_id in assigned_area_ids

