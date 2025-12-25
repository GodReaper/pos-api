from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime, timezone
from app.db import mongo
from app.models.order import OrderInDB, Order
from bson import ObjectId
from app.core.timezone import now_ist, ist_to_utc


async def get_order_by_id(order_id: str) -> Optional[Order]:
    """Get an order by ID"""
    if mongo.db is None:
        return None
    
    try:
        order_doc = await mongo.db.orders.find_one({"_id": ObjectId(order_id)})
        if order_doc:
            return Order.from_db(order_doc)
    except Exception:
        pass
    return None


async def get_order_by_table_id(table_id: str) -> Optional[Order]:
    """Get current order for a table"""
    if mongo.db is None:
        return None
    
    try:
        # Find the most recent open order for this table
        order_doc = await mongo.db.orders.find_one(
            {
                "table_id": ObjectId(table_id),
                "status": {"$in": ["open", "kot_printed", "billed"]}
            },
            sort=[("created_at", -1)]
        )
        if order_doc:
            return Order.from_db(order_doc)
    except Exception:
        pass
    return None


async def get_orders_by_table(table_id: str) -> List[Order]:
    """Get all orders for a table"""
    if mongo.db is None:
        return []
    
    try:
        cursor = mongo.db.orders.find({"table_id": ObjectId(table_id)}).sort("created_at", -1)
        orders: List[Order] = []
        async for order_doc in cursor:
            orders.append(Order.from_db(order_doc))
        return orders
    except Exception:
        return []
    

async def get_orders_by_area(area_id: str) -> List[Order]:
    """Get all orders for an area"""
    if mongo.db is None:
        return []
    
    try:
        cursor = mongo.db.orders.find({"area_id": ObjectId(area_id)}).sort("created_at", -1)
        orders: List[Order] = []
        async for order_doc in cursor:
            orders.append(Order.from_db(order_doc))
        return orders
    except Exception:
        return []
    

async def create_order(order_data: OrderInDB) -> Order:
    """Create a new order"""
    if mongo.db is None:
        raise Exception("Database connection not available")
    
    order_dict = order_data.model_dump(by_alias=True, exclude={"id"})
    # Convert IDs to ObjectId
    order_dict["table_id"] = ObjectId(order_dict["table_id"])
    order_dict["area_id"] = ObjectId(order_dict["area_id"])
    order_dict["created_by"] = ObjectId(order_dict["created_by"])
    if order_dict.get("cancelled_by_user_id"):
        order_dict["cancelled_by_user_id"] = ObjectId(order_dict["cancelled_by_user_id"])
    
    # Convert nested models to dicts (model_dump() already does this, but ensure consistency)
    if order_dict.get("items"):
        order_dict["items"] = [
            item.model_dump() if hasattr(item, "model_dump") else item
            for item in order_dict["items"]
        ]
    if order_dict.get("totals"):
        order_dict["totals"] = (
            order_dict["totals"].model_dump()
            if hasattr(order_dict["totals"], "model_dump")
            else order_dict["totals"]
        )
    if order_dict.get("kot_prints"):
        order_dict["kot_prints"] = [
            kot.model_dump() if hasattr(kot, "model_dump") else kot
            for kot in order_dict["kot_prints"]
        ]
    if order_dict.get("bill_prints"):
        order_dict["bill_prints"] = [
            bill.model_dump() if hasattr(bill, "model_dump") else bill
            for bill in order_dict["bill_prints"]
        ]
    if order_dict.get("payments"):
        order_dict["payments"] = [
            payment.model_dump() if hasattr(payment, "model_dump") else payment
            for payment in order_dict["payments"]
        ]
    
    # Convert IST datetime fields to UTC for MongoDB storage
    # (MongoDB stores datetimes in UTC, so we convert IST to UTC)
    if order_dict.get("created_at") and isinstance(order_dict["created_at"], datetime):
        if order_dict["created_at"].tzinfo is not None:
            order_dict["created_at"] = ist_to_utc(order_dict["created_at"])
        else:
            # If naive, assume it's already UTC or IST - set to UTC for safety
            order_dict["created_at"] = order_dict["created_at"].replace(tzinfo=timezone.utc)
    
    if order_dict.get("updated_at") and isinstance(order_dict["updated_at"], datetime):
        if order_dict["updated_at"].tzinfo is not None:
            order_dict["updated_at"] = ist_to_utc(order_dict["updated_at"])
        else:
            order_dict["updated_at"] = order_dict["updated_at"].replace(tzinfo=timezone.utc)
    
    if order_dict.get("cancelled_at") and isinstance(order_dict["cancelled_at"], datetime):
        if order_dict["cancelled_at"].tzinfo is not None:
            order_dict["cancelled_at"] = ist_to_utc(order_dict["cancelled_at"])
        else:
            order_dict["cancelled_at"] = order_dict["cancelled_at"].replace(tzinfo=timezone.utc)
    
    # Convert nested datetime fields to UTC
    if order_dict.get("kot_prints"):
        for kot in order_dict["kot_prints"]:
            if kot.get("printed_at") and isinstance(kot["printed_at"], datetime):
                if kot["printed_at"].tzinfo is not None:
                    kot["printed_at"] = ist_to_utc(kot["printed_at"])
                else:
                    kot["printed_at"] = kot["printed_at"].replace(tzinfo=timezone.utc)
    
    if order_dict.get("bill_prints"):
        for bill in order_dict["bill_prints"]:
            if bill.get("printed_at") and isinstance(bill["printed_at"], datetime):
                if bill["printed_at"].tzinfo is not None:
                    bill["printed_at"] = ist_to_utc(bill["printed_at"])
                else:
                    bill["printed_at"] = bill["printed_at"].replace(tzinfo=timezone.utc)
    
    if order_dict.get("payments"):
        for payment in order_dict["payments"]:
            if payment.get("paid_at") and isinstance(payment["paid_at"], datetime):
                if payment["paid_at"].tzinfo is not None:
                    payment["paid_at"] = ist_to_utc(payment["paid_at"])
                else:
                    payment["paid_at"] = payment["paid_at"].replace(tzinfo=timezone.utc)
    
    result = await mongo.db.orders.insert_one(order_dict)
    
    created_order = await mongo.db.orders.find_one({"_id": result.inserted_id})
    return Order.from_db(created_order)


async def update_order(order_id: str, update_data: dict) -> Optional[Order]:
    """Update an order"""
    if mongo.db is None:
        raise Exception("Database connection not available")
    
    try:
        # Remove None values
        update_dict = {k: v for k, v in update_data.items() if v is not None}
        
        # Convert IDs to ObjectId if present
        if "table_id" in update_dict:
            update_dict["table_id"] = ObjectId(update_dict["table_id"])
        if "area_id" in update_dict:
            update_dict["area_id"] = ObjectId(update_dict["area_id"])
        if "created_by" in update_dict:
            update_dict["created_by"] = ObjectId(update_dict["created_by"])
        if "cancelled_by_user_id" in update_dict and update_dict["cancelled_by_user_id"]:
            update_dict["cancelled_by_user_id"] = ObjectId(update_dict["cancelled_by_user_id"])
        
        # Convert nested models to dicts
        if "items" in update_dict:
            update_dict["items"] = [
                item.model_dump() if hasattr(item, "model_dump") else item
                for item in update_dict["items"]
            ]
        if "totals" in update_dict:
            update_dict["totals"] = (
                update_dict["totals"].model_dump()
                if hasattr(update_dict["totals"], "model_dump")
                else update_dict["totals"]
            )
        if "kot_prints" in update_dict:
            kot_prints = [
                kot.model_dump() if hasattr(kot, "model_dump") else kot
                for kot in update_dict["kot_prints"]
            ]
            # Convert IST datetime fields to UTC for MongoDB storage
            for kot in kot_prints:
                if kot.get("printed_at") and isinstance(kot["printed_at"], datetime):
                    if kot["printed_at"].tzinfo is not None:
                        kot["printed_at"] = ist_to_utc(kot["printed_at"])
                    else:
                        kot["printed_at"] = kot["printed_at"].replace(tzinfo=timezone.utc)
            update_dict["kot_prints"] = kot_prints
        if "bill_prints" in update_dict:
            bill_prints = [
                bill.model_dump() if hasattr(bill, "model_dump") else bill
                for bill in update_dict["bill_prints"]
            ]
            # Convert IST datetime fields to UTC for MongoDB storage
            for bill in bill_prints:
                if bill.get("printed_at") and isinstance(bill["printed_at"], datetime):
                    if bill["printed_at"].tzinfo is not None:
                        bill["printed_at"] = ist_to_utc(bill["printed_at"])
                    else:
                        bill["printed_at"] = bill["printed_at"].replace(tzinfo=timezone.utc)
            update_dict["bill_prints"] = bill_prints
        if "payments" in update_dict:
            payments = [
                payment.model_dump() if hasattr(payment, "model_dump") else payment
                for payment in update_dict["payments"]
            ]
            # Convert IST datetime fields to UTC for MongoDB storage
            for payment in payments:
                if payment.get("paid_at") and isinstance(payment["paid_at"], datetime):
                    if payment["paid_at"].tzinfo is not None:
                        payment["paid_at"] = ist_to_utc(payment["paid_at"])
                    else:
                        payment["paid_at"] = payment["paid_at"].replace(tzinfo=timezone.utc)
            update_dict["payments"] = payments
        
        # Convert IST datetime fields to UTC for MongoDB storage
        if "cancelled_at" in update_dict and isinstance(update_dict["cancelled_at"], datetime):
            if update_dict["cancelled_at"].tzinfo is not None:
                update_dict["cancelled_at"] = ist_to_utc(update_dict["cancelled_at"])
            else:
                update_dict["cancelled_at"] = update_dict["cancelled_at"].replace(tzinfo=timezone.utc)
        
        # Always update updated_at (convert IST to UTC for MongoDB storage)
        now_ist_dt = now_ist()
        update_dict["updated_at"] = ist_to_utc(now_ist_dt)
        
        if not update_dict:
            return await get_order_by_id(order_id)
        
        result = await mongo.db.orders.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": update_dict}
        )
        
        if result.modified_count == 0:
            return None
        
        return await get_order_by_id(order_id)
    except Exception:
        return None
    

async def order_exists(order_id: str) -> bool:
    """Check if an order exists"""
    if mongo.db is None:
        return False
    
    try:
        count = await mongo.db.orders.count_documents({"_id": ObjectId(order_id)})
        return count > 0
    except Exception:
        return False


async def list_orders_raw(
    query: Dict[str, Any],
    page: int,
    page_size: int,
    sort: Optional[List[Tuple[str, int]]] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Low-level list helper returning raw Mongo documents and total count.
    No caching; caller is responsible for projections/enrichment.
    """
    if mongo.db is None:
        return [], 0

    try:
        collection = mongo.db.orders
        total = await collection.count_documents(query)

        cursor = collection.find(query)
        if sort:
            cursor = cursor.sort(sort)

        cursor = cursor.skip((page - 1) * page_size).limit(page_size)

        items: List[Dict[str, Any]] = []
        async for doc in cursor:
            items.append(doc)

        return items, total
    except Exception:
        return [], 0
