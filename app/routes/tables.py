from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.order import Order
from app.models.user import User
from app.services.order_service import open_order, get_current_order
from app.core.rbac import require_biller
from app.services.assignment_service import is_biller_assigned_to_area
from app.repositories.table_repo import get_table_by_id

router = APIRouter(prefix="/tables", tags=["tables"])


@router.post("/{table_id}/open", response_model=Order, status_code=status.HTTP_201_CREATED)
async def open_table_order(
    table_id: str,
    current_user: User = Depends(require_biller)
):
    """Open/create an order for a table"""
    # Verify table exists and biller has access
    table = await get_table_by_id(table_id)
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )
    
    # Check if biller is assigned to the area
    if not await is_biller_assigned_to_area(current_user.id, table.area_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not assigned to this area"
        )
    
    return await open_order(table_id, current_user.id)


@router.get("/{table_id}/current", response_model=Optional[Order])
async def get_table_current_order(
    table_id: str,
    current_user: User = Depends(require_biller)
):
    """Get current order for a table"""
    # Verify table exists and biller has access
    table = await get_table_by_id(table_id)
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )
    
    # Check if biller is assigned to the area
    if not await is_biller_assigned_to_area(current_user.id, table.area_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not assigned to this area"
        )
    
    return await get_current_order(table_id)

