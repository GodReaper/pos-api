from typing import Optional, List, Tuple
from datetime import datetime, timezone
from fastapi import HTTPException, status
from app.core.timezone import (
    now_ist,
    ist_to_utc,
    get_date_range_utc_for_ist_date,
    get_today_start_ist,
    get_today_end_ist,
)
from app.models.order import (
    Order,
    OrderCreate,
    OrderItemUpdate,
    OrderItem,
    OrderTotals,
    KOTPrint,
    BillPrint,
    Payment,
    OrderListItem,
    OrderItemPreview,
)
from app.models.user import User
from app.repositories.order_repo import (
    get_order_by_id,
    get_order_by_table_id,
    create_order,
    update_order,
    order_exists,
    list_orders_raw,
)
from app.repositories.table_repo import get_table_by_id, update_table
from app.repositories.menu_item_repo import get_item_by_id
from app.repositories.area_repo import get_area_by_id
from app.repositories.user_repo import get_user_by_id
from app.db.redis import acquire_lock, release_lock, publish_event


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
    if order.status in ["paid", "closed", "cancelled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify a paid, closed, or cancelled order"
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
            printed_at=now_ist(),
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
            printed_at=now_ist(),
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


def _build_status_filter(scope: str) -> List[str] | str | None:
    """Map logical scope to underlying status filter."""
    if scope == "running":
        return ["open", "kot_printed", "billed"]
    if scope == "closed":
        return ["paid", "closed"]
    if scope == "cancelled":
        return "cancelled"
    # "all" or anything else -> no explicit filter
    return None


async def list_orders_service(
    scope: str,
    page: int,
    page_size: int,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    biller_id: Optional[str] = None,
    text: Optional[str] = None,
) -> Tuple[List[OrderListItem], int]:
    """
    High-level listing with filters, enrichment (table/area names, biller username),
    pagination and lightweight items preview.
    
    Note: from_date and to_date should be in IST timezone. They will be converted
    to UTC for database queries since MongoDB stores dates in UTC.
    """
    # Base query
    query: dict = {}

    status_filter = _build_status_filter(scope)
    if isinstance(status_filter, list):
        query["status"] = {"$in": status_filter}
    elif isinstance(status_filter, str):
        query["status"] = status_filter

    # Date range - convert IST to UTC for database query
    if from_date or to_date:
        created_at_filter: dict = {}
        if from_date:
            # Convert IST datetime to UTC for MongoDB query
            utc_from = ist_to_utc(from_date)
            created_at_filter["$gte"] = utc_from
        if to_date:
            # Convert IST datetime to UTC for MongoDB query
            utc_to = ist_to_utc(to_date)
            created_at_filter["$lte"] = utc_to
        query["created_at"] = created_at_filter

    # Biller filter
    if biller_id:
        from bson import ObjectId  # local import to avoid top-level dependency here
        try:
            query["created_by"] = ObjectId(biller_id)
        except Exception:
            # Invalid ObjectId -> no results
            return [], 0

    # Text search: table name or exact order id match
    from app.db import mongo as _mongo_mod  # lazy import
    table_ids_for_text: Optional[List[ObjectId]] = None
    order_id_filter_oid = None
    if text and _mongo_mod.db is not None:
        from bson import ObjectId as _OID

        # Attempt exact order id match
        if _OID.is_valid(text):
            order_id_filter_oid = _OID(text)

        # Collect table ids with matching name
        try:
            cursor = _mongo_mod.db.tables.find(
                {"name": {"$regex": text, "$options": "i"}},
                projection={"_id": 1},
            )
            table_ids_for_text = []
            async for t in cursor:
                table_ids_for_text.append(t["_id"])
        except Exception:
            table_ids_for_text = None

        or_clauses: List[dict] = []
        if order_id_filter_oid is not None:
            or_clauses.append({"_id": order_id_filter_oid})
        if table_ids_for_text:
            or_clauses.append({"table_id": {"$in": table_ids_for_text}})

        if or_clauses:
            query["$or"] = or_clauses

    # Sort: newest first
    sort = [("created_at", -1)]

    raw_docs, total = await list_orders_raw(query, page=page, page_size=page_size, sort=sort)

    if not raw_docs:
        return [], total

    # Collect related ids for enrichment
    table_ids: List[str] = []
    area_ids: List[str] = []
    biller_ids: List[str] = []
    for doc in raw_docs:
        if doc.get("table_id"):
            table_ids.append(str(doc["table_id"]))
        if doc.get("area_id"):
            area_ids.append(str(doc["area_id"]))
        if doc.get("created_by"):
            biller_ids.append(str(doc["created_by"]))

    # Simple per-doc lookups via existing repositories (keeps logic centralized)
    # For typical POS volumes this is acceptable; can be optimized to batch later.
    tables_cache: dict[str, str] = {}
    areas_cache: dict[str, str] = {}
    users_cache: dict[str, str] = {}

    async def _get_table_name(table_id: str) -> Optional[str]:
        if table_id in tables_cache:
            return tables_cache[table_id]
        table = await get_table_by_id(table_id)
        name = table.name if table else None
        tables_cache[table_id] = name
        return name

    async def _get_area_name(area_id: str) -> Optional[str]:
        if area_id in areas_cache:
            return areas_cache[area_id]
        area = await get_area_by_id(area_id)
        name = area.name if area else None
        areas_cache[area_id] = name
        return name

    async def _get_username(user_id: str) -> Optional[str]:
        if user_id in users_cache:
            return users_cache[user_id]
        user = await get_user_by_id(user_id)
        username = user.username if user else None
        users_cache[user_id] = username
        return username

    items: List[OrderListItem] = []
    for doc in raw_docs:
        order = Order.from_db(doc)

        # Items count and preview
        items_count = sum(i.qty for i in order.items)
        previews: List[OrderItemPreview] = []
        for item in order.items[:3]:
            previews.append(
                OrderItemPreview(
                    name=item.name_snapshot,
                    qty=item.qty,
                    price=item.price_snapshot,
                )
            )

        table_name = await _get_table_name(order.table_id)
        area_name = await _get_area_name(order.area_id)
        created_by_username = await _get_username(order.created_by)

        items.append(
            OrderListItem(
                id=order.id,
                status=order.status,
                area_id=order.area_id,
                table_id=order.table_id,
                table_name=table_name,
                area_name=area_name,
                created_by=order.created_by,
                created_by_username=created_by_username,
                created_at=order.created_at,
                updated_at=order.updated_at,
                grand_total=order.totals.grand_total,
                items_count=items_count,
                items_preview=previews,
            )
        )

    return items, total


async def cancel_order_service(order_id: str, user: User, reason: str) -> Order:
    """
    Cancel an order with permission checks and side effects.
    - Does not delete payments or audit trail.
    - Clears table.current_order_id + sets table.status='available' if currently open.
    - Publishes Redis pub/sub events on pos:admin and pos:area:{area_id}.
    """
    reason = (reason or "").strip()
    if not reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cancellation reason is required",
        )

    order = await get_order_by_id(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    if order.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Order is already cancelled",
        )

    # Permissions
    if user.role == "admin":
        allowed = True
    elif user.role == "biller":
        allowed = order.created_by == user.id
    else:
        allowed = False

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to cancel this order",
        )

    now = now_ist()

    update_data = {
        "status": "cancelled",
        "cancelled_at": now,
        "cancelled_by_user_id": user.id,
        "cancelled_by_role": user.role,
        "cancel_reason": reason,
    }

    updated_order = await update_order(order_id, update_data)
    if not updated_order:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update order",
        )

    # If table currently points to this order, clear it and mark available
    table = await get_table_by_id(updated_order.table_id)
    if table and table.current_order_id == updated_order.id:
        await update_table(
            updated_order.table_id,
            {
                "status": "available",
                "current_order_id": None,
            },
        )

    # Publish Redis events (best-effort)
    payload = {
        "type": "order_cancelled",
        "order_id": updated_order.id,
        "area_id": updated_order.area_id,
        "table_id": updated_order.table_id,
        "status": updated_order.status,
        "cancelled_at": updated_order.cancelled_at.isoformat()
        if updated_order.cancelled_at
        else None,
        "cancelled_by_role": updated_order.cancelled_by_role,
    }

    await publish_event("pos:admin", payload)
    await publish_event(f"pos:area:{updated_order.area_id}", payload)

    return updated_order
