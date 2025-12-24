from typing import Optional, List
from datetime import datetime
from app.db import mongo
from app.models.area import AreaInDB, Area
from bson import ObjectId


async def get_area_by_id(area_id: str) -> Optional[Area]:
    """Get an area by ID"""
    if mongo.db is None:
        return None
    
    try:
        area_doc = await mongo.db.areas.find_one({"_id": ObjectId(area_id)})
        if area_doc:
            return Area.from_db(area_doc)
    except Exception:
        pass
    return None


async def get_all_areas() -> List[Area]:
    """Get all areas sorted by sort_order"""
    if mongo.db is None:
        return []
    
    cursor = mongo.db.areas.find().sort("sort_order", 1)
    areas = []
    async for area_doc in cursor:
        areas.append(Area.from_db(area_doc))
    return areas


async def create_area(area_data: AreaInDB) -> Area:
    """Create a new area"""
    if mongo.db is None:
        raise Exception("Database connection not available")
    
    area_dict = area_data.model_dump(by_alias=True, exclude={"id"})
    result = await mongo.db.areas.insert_one(area_dict)
    
    created_area = await mongo.db.areas.find_one({"_id": result.inserted_id})
    return Area.from_db(created_area)


async def update_area(area_id: str, update_data: dict) -> Optional[Area]:
    """Update an area"""
    if mongo.db is None:
        raise Exception("Database connection not available")
    
    try:
        # Remove None values
        update_dict = {k: v for k, v in update_data.items() if v is not None}
        
        if not update_dict:
            return await get_area_by_id(area_id)
        
        result = await mongo.db.areas.update_one(
            {"_id": ObjectId(area_id)},
            {"$set": update_dict}
        )
        
        if result.modified_count == 0:
            return None
        
        return await get_area_by_id(area_id)
    except Exception:
        return None


async def delete_area(area_id: str) -> bool:
    """Delete an area"""
    if mongo.db is None:
        raise Exception("Database connection not available")
    
    try:
        result = await mongo.db.areas.delete_one({"_id": ObjectId(area_id)})
        return result.deleted_count > 0
    except Exception:
        return False


async def area_exists(area_id: str) -> bool:
    """Check if an area exists"""
    if mongo.db is None:
        return False
    
    try:
        count = await mongo.db.areas.count_documents({"_id": ObjectId(area_id)})
        return count > 0
    except Exception:
        return False

