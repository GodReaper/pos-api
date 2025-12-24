from typing import Optional
from fastapi import HTTPException, status
from app.models.order import (
    Order, OrderCreate, OrderItemUpdate, OrderItem, OrderTotals,
    KOTPrint, BillPrint, Payment
)
from app.repositories.order_repo import (
    get_order_by_id,
    get_order_by_table_id,
    create_order,
    update_order,
    order_exists
)
from app.repositories.table_repo import get_table_by_id, update_table
from app.repositories.menu_item_repo import get_item_by_id
from app.db.redis import acquire_lock, release_lock
from datetime import datetime


# Tax rate (can be made configurable later)
TAX_RATE = 0.0  # 0% by default, adjust as needed


def calculate_totals(items: list[OrderItem], discount_total: float = 0.0) -> OrderTotals:
    """Calculate order totals from items"""
    sub_total = sum(item.price_snapshot * item.qty for item in items)
    tax_total = sub_total * TAX_RATE
    grand_total = sub_total + tax_total - discount_total
    
    return OrderTotals(
        sub_total=round(sub_total, 2),
        tax_total=round(tax_total, 2),
        discount_total=round(discount_total, 2),
        grand_total=round(grand_total, 2)
    )


async def open_order(table_id: str, user_id: str) -> Order:
    """Open/create an order for a table"""
    # Check if table exists
    table = await get_table_by_id(table_id)
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )
    
    # Check if table already has an open order
    existing_order = await get_order_by_table_id(table_id)
    if existing_order:
        # Return existing order if it's still open
        if existing_order.status in ["open", "kot_printed", "billed"]:
            return existing_order
    
    # Create new order
    order_data = OrderCreate(
        table_id=table_id,
        area_id=table.area_id,
        created_by=user_id
    )
    
    order_in_db = order_data.model_dump()
    order_in_db["status"] = "open"
    order_in_db["items"] = []
    order_in_db["totals"] = OrderTotals().model_dump()
    order_in_db["kot_prints"] = []
    order_in_db["bill_prints"] = []
    order_in_db["payments"] = []
    
    from app.models.order import OrderInDB
    new_order = await create_order(OrderInDB(**order_in_db))
    
    # Update table status
    await update_table(table_id, {
        "status": "occupied",
        "current_order_id": new_order.id
    })
    
    return new_order


async def add_order_item(order_id: str, item_update: OrderItemUpdate, user_id: str) -> Order:
    """Add or update quantity of an item in an order"""
    order = await get_order_by_id(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check if order can be modified
    if order.status in ["paid", "closed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify a paid or closed order"
        )
    
    # Get menu item to get current name and price
    menu_item = await get_item_by_id(item_update.item_id)
    if not menu_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu item not found"
        )
    
    if not menu_item.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Menu item is not active"
        )
    
    # Find existing item in order
    existing_item_index = None
    for i, item in enumerate(order.items):
        if item.item_id == item_update.item_id:
            existing_item_index = i
            break
    
    # Update or add item
    if existing_item_index is not None:
        # Update existing item
        new_qty = order.items[existing_item_index].qty + item_update.qty_delta
        if new_qty <= 0:
            # Remove item if quantity becomes 0 or negative
            order.items.pop(existing_item_index)
        else:
            # Update quantity and notes
            order.items[existing_item_index].qty = new_qty
            if item_update.notes is not None:
                order.items[existing_item_index].notes = item_update.notes
    else:
        # Add new item
        if item_update.qty_delta <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot add item with zero or negative quantity"
            )
        
        new_item = OrderItem(
            item_id=item_update.item_id,
            name_snapshot=menu_item.name,
            price_snapshot=menu_item.price,
            qty=item_update.qty_delta,
            notes=item_update.notes
        )
        order.items.append(new_item)
    
    # Recalculate totals
    order.totals = calculate_totals(order.items, order.totals.discount_total)
    
    # Update order
    update_data = {
        "items": [item.model_dump() for item in order.items],
        "totals": order.totals.model_dump()
    }
    
    updated_order = await update_order(order_id, update_data)
    if not updated_order:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update order"
        )
    
    return updated_order


async def print_kot(order_id: str) -> Order:
    """Print KOT (Kitchen Order Ticket) for an order"""
    # Acquire lock to prevent duplicate prints
    lock_key = f"kot:{order_id}"
    if not await acquire_lock(lock_key, ttl=2):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="KOT print already in progress, please wait"
        )
    
    try:
        order = await get_order_by_id(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        if not order.items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot print KOT for order with no items"
            )
        
        # Create KOT print record
        kot_print = KOTPrint(
            printed_at=datetime.utcnow(),
            items_snapshot=[item.model_dump() for item in order.items]
        )
        
        # Add to kot_prints and update status
        order.kot_prints.append(kot_print)
        new_status = "kot_printed" if order.status == "open" else order.status
        
        update_data = {
            "kot_prints": [kot.model_dump() for kot in order.kot_prints],
            "status": new_status
        }
        
        updated_order = await update_order(order_id, update_data)
        if not updated_order:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update order"
            )
        
        return updated_order
    finally:
        await release_lock(lock_key)


async def print_bill(order_id: str) -> Order:
    """Print bill for an order"""
    # Acquire lock to prevent duplicate prints
    lock_key = f"bill:{order_id}"
    if not await acquire_lock(lock_key, ttl=2):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Bill print already in progress, please wait"
        )
    
    try:
        order = await get_order_by_id(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        if not order.items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot print bill for order with no items"
            )
        
        # Create bill print record
        bill_print = BillPrint(
            printed_at=datetime.utcnow(),
            totals_snapshot=order.totals.model_dump()
        )
        
        # Add to bill_prints and update status
        order.bill_prints.append(bill_print)
        
        update_data = {
            "bill_prints": [bill.model_dump() for bill in order.bill_prints],
            "status": "billed"
        }
        
        updated_order = await update_order(order_id, update_data)
        if not updated_order:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update order"
            )
        
        return updated_order
    finally:
        await release_lock(lock_key)


async def process_payment(order_id: str, payments: list[Payment]) -> Order:
    """Process payment for an order and close it"""
    order = await get_order_by_id(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    if order.status != "billed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order must be billed before payment"
        )
    
    # Validate payment amounts
    total_payment = sum(payment.amount for payment in payments)
    if total_payment < order.totals.grand_total:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Total payment ({total_payment}) is less than grand total ({order.totals.grand_total})"
        )
    
    # Add payments to order
    order.payments.extend(payments)
    
    # Update order status to paid and then closed
    update_data = {
        "payments": [payment.model_dump() for payment in order.payments],
        "status": "paid"
    }
    
    updated_order = await update_order(order_id, update_data)
    if not updated_order:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update order"
        )
    
    # Close the order
    await update_order(order_id, {"status": "closed"})
    updated_order = await get_order_by_id(order_id)
    
    # Clear table
    table = await get_table_by_id(order.table_id)
    if table:
        await update_table(order.table_id, {
            "status": "available",
            "current_order_id": None
        })
    
    return updated_order


async def get_current_order(table_id: str) -> Optional[Order]:
    """Get current order for a table"""
    table = await get_table_by_id(table_id)
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )
    
    if not table.current_order_id:
        return None
    
    order = await get_order_by_id(table.current_order_id)
    return order

