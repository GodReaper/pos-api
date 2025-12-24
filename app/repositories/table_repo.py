from typing import Optional, List
from datetime import datetime
from app.db import mongo
from app.models.table import TableInDB, Table
from bson import ObjectId


async def get_table_by_id(table_id: str) -> Optional[Table]:
    """Get a table by ID"""
    if mongo.db is None:
        return None
    
    try:
        table_doc = await mongo.db.tables.find_one({"_id": ObjectId(table_id)})
        if table_doc:
            return Table.from_db(table_doc)
    except Exception:
        pass
    return None


async def get_tables_by_area(area_id: str) -> List[Table]:
    """Get all tables for an area"""
    if mongo.db is None:
        return []
    
    try:
        cursor = mongo.db.tables.find({"area_id": ObjectId(area_id)})
        tables = []
        async for table_doc in cursor:
            tables.append(Table.from_db(table_doc))
        return tables
    except Exception:
        return []


async def get_tables_by_area_ids(area_ids: List[str]) -> List[Table]:
    """Get all tables for multiple areas"""
    if mongo.db is None:
        return []
    
    try:
        object_ids = [ObjectId(aid) for aid in area_ids]
        cursor = mongo.db.tables.find({"area_id": {"$in": object_ids}})
        tables = []
        async for table_doc in cursor:
            tables.append(Table.from_db(table_doc))
        return tables
    except Exception:
        return []


async def create_table(table_data: TableInDB) -> Table:
    """Create a new table"""
    if mongo.db is None:
        raise Exception("Database connection not available")
    
    table_dict = table_data.model_dump(by_alias=True, exclude={"id"})
    # Convert area_id and current_order_id to ObjectId
    table_dict["area_id"] = ObjectId(table_dict["area_id"])
    if table_dict.get("current_order_id"):
        table_dict["current_order_id"] = ObjectId(table_dict["current_order_id"])
    # Convert position to dict if present
    if table_dict.get("position"):
        table_dict["position"] = table_dict["position"].model_dump() if hasattr(table_dict["position"], "model_dump") else table_dict["position"]
    
    result = await mongo.db.tables.insert_one(table_dict)
    
    created_table = await mongo.db.tables.find_one({"_id": result.inserted_id})
    return Table.from_db(created_table)


async def update_table(table_id: str, update_data: dict) -> Optional[Table]:
    """Update a table"""
    if mongo.db is None:
        raise Exception("Database connection not available")
    
    try:
        # Remove None values
        update_dict = {k: v for k, v in update_data.items() if v is not None}
        
        # Convert area_id and current_order_id to ObjectId if present
        if "area_id" in update_dict:
            update_dict["area_id"] = ObjectId(update_dict["area_id"])
        if "current_order_id" in update_dict:
            update_dict["current_order_id"] = ObjectId(update_dict["current_order_id"])
        # Convert position to dict if present
        if "position" in update_dict and update_dict["position"]:
            update_dict["position"] = update_dict["position"].model_dump() if hasattr(update_dict["position"], "model_dump") else update_dict["position"]
        
        # Always update updated_at
        update_dict["updated_at"] = datetime.utcnow()
        
        if not update_dict:
            return await get_table_by_id(table_id)
        
        result = await mongo.db.tables.update_one(
            {"_id": ObjectId(table_id)},
            {"$set": update_dict}
        )
        
        if result.modified_count == 0:
            return None
        
        return await get_table_by_id(table_id)
    except Exception:
        return None


async def delete_table(table_id: str) -> bool:
    """Delete a table"""
    if mongo.db is None:
        raise Exception("Database connection not available")
    
    try:
        result = await mongo.db.tables.delete_one({"_id": ObjectId(table_id)})
        return result.deleted_count > 0
    except Exception:
        return False


async def table_exists(table_id: str) -> bool:
    """Check if a table exists"""
    if mongo.db is None:
        return False
    
    try:
        count = await mongo.db.tables.count_documents({"_id": ObjectId(table_id)})
        return count > 0
    except Exception:
        return False

