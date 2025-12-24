from typing import List, Optional
from fastapi import HTTPException, status
from app.models.area import AreaCreate, AreaUpdate, Area, AreaInDB
from app.repositories.area_repo import (
    get_area_by_id,
    get_all_areas,
    create_area,
    update_area,
    delete_area,
    area_exists
)


async def get_areas() -> List[Area]:
    """Get all areas"""
    return await get_all_areas()


async def get_area(area_id: str) -> Area:
    """Get an area by ID"""
    area = await get_area_by_id(area_id)
    if not area:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Area not found"
        )
    return area


async def create_area_service(area_data: AreaCreate) -> Area:
    """Create a new area"""
    area_in_db = AreaInDB(**area_data.model_dump())
    return await create_area(area_in_db)


async def update_area_service(area_id: str, area_data: AreaUpdate) -> Area:
    """Update an area"""
    if not await area_exists(area_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Area not found"
        )
    
    update_dict = area_data.model_dump(exclude_unset=True)
    updated_area = await update_area(area_id, update_dict)
    
    if not updated_area:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Area not found"
        )
    
    return updated_area


async def delete_area_service(area_id: str) -> bool:
    """Delete an area"""
    if not await area_exists(area_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Area not found"
        )
    
    # Check if area has tables
    from app.repositories.table_repo import get_tables_by_area
    tables = await get_tables_by_area(area_id)
    if tables:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete area with existing tables. Please delete or move tables first."
        )
    
    return await delete_area(area_id)

