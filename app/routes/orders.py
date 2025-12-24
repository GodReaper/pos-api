from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.order import Order, OrderItemUpdate, Payment
from app.models.user import User
from app.services.order_service import (
    open_order,
    add_order_item,
    print_kot,
    print_bill,
    process_payment,
    get_current_order
)
from app.core.rbac import require_biller
from app.services.assignment_service import is_biller_assigned_to_area
from app.repositories.order_repo import get_order_by_id

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/{order_id}/items", response_model=Order)
async def update_order_items(
    order_id: str,
    item_update: OrderItemUpdate,
    current_user: User = Depends(require_biller)
):
    """Add or update items in an order"""
    # Verify order exists and biller has access
    order = await get_order_by_id(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check if biller is assigned to the area
    if not await is_biller_assigned_to_area(current_user.id, order.area_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not assigned to this area"
        )
    
    return await add_order_item(order_id, item_update, current_user.id)


@router.post("/{order_id}/kot", response_model=Order)
async def print_order_kot(
    order_id: str,
    current_user: User = Depends(require_biller)
):
    """Print KOT (Kitchen Order Ticket) for an order"""
    # Verify order exists and biller has access
    order = await get_order_by_id(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check if biller is assigned to the area
    if not await is_biller_assigned_to_area(current_user.id, order.area_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not assigned to this area"
        )
    
    return await print_kot(order_id)


@router.post("/{order_id}/bill", response_model=Order)
async def print_order_bill(
    order_id: str,
    current_user: User = Depends(require_biller)
):
    """Print bill for an order"""
    # Verify order exists and biller has access
    order = await get_order_by_id(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check if biller is assigned to the area
    if not await is_biller_assigned_to_area(current_user.id, order.area_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not assigned to this area"
        )
    
    return await print_bill(order_id)


@router.post("/{order_id}/payment", response_model=Order)
async def process_order_payment(
    order_id: str,
    payments: List[Payment],
    current_user: User = Depends(require_biller)
):
    """Process payment for an order"""
    # Verify order exists and biller has access
    order = await get_order_by_id(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check if biller is assigned to the area
    if not await is_biller_assigned_to_area(current_user.id, order.area_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not assigned to this area"
        )
    
    return await process_payment(order_id, payments)

