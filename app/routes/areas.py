import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.area import Area, AreaCreate, AreaUpdate
from app.models.table import Table, TableCreate, TableUpdate
from app.services.area_service import (
    get_areas,
    get_area,
    create_area_service,
    update_area_service,
    delete_area_service
)
from app.services.table_service import (
    get_tables,
    get_table,
    create_table_service,
    update_table_service,
    delete_table_service
)
from app.services.assignment_service import (
    get_assigned_areas_for_biller,
    is_biller_assigned_to_area
)
from app.core.rbac import require_admin, require_biller, get_current_user
from app.models.user import User
from app.db.redis import get_cache, set_cache, delete_cache

# Admin router for areas
admin_router = APIRouter(prefix="/admin", tags=["admin"])
# Biller router for areas
biller_router = APIRouter(prefix="/areas", tags=["areas"])


# Admin endpoints for areas
@admin_router.get("/areas", response_model=List[Area], dependencies=[Depends(require_admin)])
async def list_areas():
    """Get all areas (admin only)"""
    return await get_areas()


@admin_router.post("/areas", response_model=Area, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
async def create_area(area_data: AreaCreate):
    """Create a new area (admin only)"""
    return await create_area_service(area_data)


@admin_router.get("/areas/{area_id}", response_model=Area, dependencies=[Depends(require_admin)])
async def get_area_by_id(area_id: str):
    """Get an area by ID (admin only)"""
    return await get_area(area_id)


@admin_router.put("/areas/{area_id}", response_model=Area, dependencies=[Depends(require_admin)])
async def update_area(area_id: str, area_data: AreaUpdate):
    """Update an area (admin only)"""
    return await update_area_service(area_id, area_data)


@admin_router.delete("/areas/{area_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
async def delete_area(area_id: str):
    """Delete an area (admin only)"""
    await delete_area_service(area_id)
    return None


# Admin endpoints for tables
@admin_router.get("/areas/{area_id}/tables", response_model=List[Table], dependencies=[Depends(require_admin)])
async def list_tables(area_id: str):
    """Get all tables for an area (admin only)"""
    return await get_tables(area_id)


@admin_router.post("/areas/{area_id}/tables", response_model=Table, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
async def create_table(area_id: str, table_data: TableCreate):
    """Create a new table in an area (admin only)"""
    return await create_table_service(area_id, table_data)


@admin_router.get("/areas/{area_id}/tables/{table_id}", response_model=Table, dependencies=[Depends(require_admin)])
async def get_table_by_id(area_id: str, table_id: str):
    """Get a table by ID (admin only)"""
    table = await get_table(table_id)
    # Verify table belongs to area
    if table.area_id != area_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found in this area"
        )
    return table


@admin_router.put("/areas/{area_id}/tables/{table_id}", response_model=Table, dependencies=[Depends(require_admin)])
async def update_table(area_id: str, table_id: str, table_data: TableUpdate):
    """Update a table (admin only)"""
    table = await get_table(table_id)
    # Verify table belongs to area
    if table.area_id != area_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found in this area"
        )
    return await update_table_service(table_id, table_data)


@admin_router.delete("/areas/{area_id}/tables/{table_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
async def delete_table(area_id: str, table_id: str):
    """Delete a table (admin only)"""
    table = await get_table(table_id)
    # Verify table belongs to area
    if table.area_id != area_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found in this area"
        )
    await delete_table_service(table_id)
    return None


# Biller endpoints
@biller_router.get("", response_model=List[Area], dependencies=[Depends(require_biller)])
async def get_biller_areas(current_user: User = Depends(get_current_user)):
    """Get areas assigned to the current biller"""
    assigned_area_ids = await get_assigned_areas_for_biller(current_user.id)
    if not assigned_area_ids:
        return []
    
    # Get all areas and filter by assigned area IDs
    all_areas = await get_areas()
    return [area for area in all_areas if area.id in assigned_area_ids]


@biller_router.get("/{area_id}/tables", response_model=List[Table], dependencies=[Depends(require_biller)])
async def get_biller_tables(area_id: str, current_user: User = Depends(get_current_user)):
    """Get tables for an area (only if biller is assigned to that area) with Redis caching"""
    # Check if biller is assigned to this area
    if not await is_biller_assigned_to_area(current_user.id, area_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not assigned to this area"
        )
    
    # Try to get from cache (canvas snapshot)
    cache_key = f"area_tables:{area_id}"
    cached_data = await get_cache(cache_key)
    if cached_data:
        try:
            tables_data = json.loads(cached_data)
            return [Table(**table) for table in tables_data]
        except Exception:
            # If cache is corrupted, continue to fetch from DB
            pass
    
    # Fetch from database
    tables = await get_tables(area_id)
    
    # Cache the result (canvas snapshot) with 2 second TTL
    try:
        tables_json = json.dumps([table.model_dump() for table in tables])
        await set_cache(cache_key, tables_json, ttl=2)
    except Exception:
        # If caching fails, continue without caching
        pass
    
    return tables
