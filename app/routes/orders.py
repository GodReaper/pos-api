from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from app.core.timezone import (
    parse_date_as_ist,
    get_today_start_ist,
    get_today_end_ist,
)
from app.models.order import Order, OrderItemUpdate, Payment, OrderListItem
from app.models.user import User
from app.services.order_service import (
    open_order,
    add_order_item,
    print_kot,
    print_bill,
    process_payment,
    get_current_order,
    list_orders_service,
    cancel_order_service,
)
from app.core.rbac import require_biller, require_admin_or_biller
from app.services.assignment_service import is_biller_assigned_to_area
from app.repositories.order_repo import get_order_by_id

router = APIRouter(prefix="/orders", tags=["orders"])


class PaginatedOrdersResponse(BaseModel):
    items: List[OrderListItem]
    page: int
    page_size: int
    total: int


@router.get("", response_model=PaginatedOrdersResponse)
async def list_orders(
    scope: str = Query("running", regex="^(running|closed|cancelled|all)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    biller_id: Optional[str] = Query(None),
    current_user: User = Depends(require_admin_or_biller),
):
    """
    List orders with filters and pagination.
    - scope: running|closed|cancelled|all (default running)
    - from/to: YYYY-MM-DD (optional, defaults to today in IST if not specified)
    - biller_id: filter by creator (admin only)
    
    All dates are interpreted in IST (Indian Standard Time, UTC+5:30).
    If from/to dates are not provided, defaults to today's date range in IST.
    """
    # Enforce biller_id filter only for admin
    effective_biller_id = biller_id
    if current_user.role != "admin":
        effective_biller_id = None

    # Parse dates as IST day bounds, default to today if not provided
    from_dt = parse_date_as_ist(from_date) if from_date else get_today_start_ist()
    to_dt = parse_date_as_ist(to_date) if to_date else get_today_end_ist()
    
    # If both dates provided, ensure from <= to
    if from_dt and to_dt and from_dt > to_dt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="from_date must be less than or equal to to_date"
        )

    items, total = await list_orders_service(
        scope=scope,
        page=page,
        page_size=page_size,
        from_date=from_dt,
        to_date=to_dt,
        biller_id=effective_biller_id,
        text=None,
    )

    return PaginatedOrdersResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/{order_id}", response_model=Order)
async def get_order(
    order_id: str,
    current_user: User = Depends(require_biller)
):
    """Get a single order by ID"""
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

    return order


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


class CancelOrderRequest(BaseModel):
    reason: str


@router.post("/{order_id}/cancel", response_model=Order)
async def cancel_order(
    order_id: str,
    body: CancelOrderRequest,
    current_user: User = Depends(require_admin_or_biller),
):
    """
    Cancel an order.
    - Admin can cancel any order.
    - Biller can cancel only their own orders.
    """
    return await cancel_order_service(order_id, current_user, body.reason)
