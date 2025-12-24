from typing import Optional, List
from datetime import datetime
from app.db import mongo
from app.models.order import OrderInDB, Order
from bson import ObjectId


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
        orders = []
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
        orders = []
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
    
    # Convert nested models to dicts
    if order_dict.get("items"):
        order_dict["items"] = [item.model_dump() if hasattr(item, "model_dump") else item for item in order_dict["items"]]
    if order_dict.get("totals"):
        order_dict["totals"] = order_dict["totals"].model_dump() if hasattr(order_dict["totals"], "model_dump") else order_dict["totals"]
    if order_dict.get("kot_prints"):
        order_dict["kot_prints"] = [kot.model_dump() if hasattr(kot, "model_dump") else kot for kot in order_dict["kot_prints"]]
    if order_dict.get("bill_prints"):
        order_dict["bill_prints"] = [bill.model_dump() if hasattr(bill, "model_dump") else bill for bill in order_dict["bill_prints"]]
    if order_dict.get("payments"):
        order_dict["payments"] = [payment.model_dump() if hasattr(payment, "model_dump") else payment for payment in order_dict["payments"]]
    
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
        
        # Convert nested models to dicts
        if "items" in update_dict:
            update_dict["items"] = [item.model_dump() if hasattr(item, "model_dump") else item for item in update_dict["items"]]
        if "totals" in update_dict:
            update_dict["totals"] = update_dict["totals"].model_dump() if hasattr(update_dict["totals"], "model_dump") else update_dict["totals"]
        if "kot_prints" in update_dict:
            update_dict["kot_prints"] = [kot.model_dump() if hasattr(kot, "model_dump") else kot for kot in update_dict["kot_prints"]]
        if "bill_prints" in update_dict:
            update_dict["bill_prints"] = [bill.model_dump() if hasattr(bill, "model_dump") else bill for bill in update_dict["bill_prints"]]
        if "payments" in update_dict:
            update_dict["payments"] = [payment.model_dump() if hasattr(payment, "model_dump") else payment for payment in update_dict["payments"]]
        
        # Always update updated_at
        update_dict["updated_at"] = datetime.utcnow()
        
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

