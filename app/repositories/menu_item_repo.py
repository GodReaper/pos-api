from typing import Optional, List
from datetime import datetime
from app.db import mongo
from app.models.menu import MenuItemInDB, MenuItem
from bson import ObjectId


async def get_item_by_id(item_id: str) -> Optional[MenuItem]:
    """Get a menu item by ID"""
    if mongo.db is None:
        return None
    
    try:
        item_doc = await mongo.db.menu_items.find_one({"_id": ObjectId(item_id)})
        if item_doc:
            return MenuItem.from_db(item_doc)
    except Exception:
        pass
    return None


async def get_items_by_category(category_id: str, include_inactive: bool = False) -> List[MenuItem]:
    """Get all menu items for a category"""
    if mongo.db is None:
        return []
    
    query = {"category_id": ObjectId(category_id)}
    if not include_inactive:
        query["is_active"] = True
    
    cursor = mongo.db.menu_items.find(query).sort("name", 1)
    items = []
    async for item_doc in cursor:
        items.append(MenuItem.from_db(item_doc))
    return items


async def get_all_items(include_inactive: bool = False) -> List[MenuItem]:
    """Get all menu items"""
    if mongo.db is None:
        return []
    
    query = {}
    if not include_inactive:
        query["is_active"] = True
    
    cursor = mongo.db.menu_items.find(query).sort("name", 1)
    items = []
    async for item_doc in cursor:
        items.append(MenuItem.from_db(item_doc))
    return items


async def create_item(item_data: MenuItemInDB) -> MenuItem:
    """Create a new menu item"""
    if mongo.db is None:
        raise Exception("Database connection not available")
    
    item_dict = item_data.model_dump(by_alias=True, exclude={"id"})
    # Convert category_id string to ObjectId
    item_dict["category_id"] = ObjectId(item_dict["category_id"])
    result = await mongo.db.menu_items.insert_one(item_dict)
    
    created_item = await mongo.db.menu_items.find_one({"_id": result.inserted_id})
    return MenuItem.from_db(created_item)


async def update_item(item_id: str, update_data: dict) -> Optional[MenuItem]:
    """Update a menu item"""
    if mongo.db is None:
        raise Exception("Database connection not available")
    
    try:
        # Remove None values
        update_dict = {k: v for k, v in update_data.items() if v is not None}
        
        # Convert category_id to ObjectId if present
        if "category_id" in update_dict:
            update_dict["category_id"] = ObjectId(update_dict["category_id"])
        
        if not update_dict:
            return await get_item_by_id(item_id)
        
        result = await mongo.db.menu_items.update_one(
            {"_id": ObjectId(item_id)},
            {"$set": update_dict}
        )
        
        if result.modified_count == 0:
            return None
        
        return await get_item_by_id(item_id)
    except Exception:
        return None


async def delete_item(item_id: str) -> bool:
    """Delete a menu item"""
    if mongo.db is None:
        raise Exception("Database connection not available")
    
    try:
        result = await mongo.db.menu_items.delete_one({"_id": ObjectId(item_id)})
        return result.deleted_count > 0
    except Exception:
        return False


async def item_exists(item_id: str) -> bool:
    """Check if an item exists"""
    if mongo.db is None:
        return False
    
    try:
        count = await mongo.db.menu_items.count_documents({"_id": ObjectId(item_id)})
        return count > 0
    except Exception:
        return False

