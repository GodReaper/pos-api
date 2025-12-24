from typing import Optional, List
from datetime import datetime
from app.db import mongo
from app.models.menu import MenuCategoryInDB, MenuCategory
from bson import ObjectId


async def get_category_by_id(category_id: str) -> Optional[MenuCategory]:
    """Get a menu category by ID"""
    if mongo.db is None:
        return None
    
    try:
        category_doc = await mongo.db.menu_categories.find_one({"_id": ObjectId(category_id)})
        if category_doc:
            return MenuCategory.from_db(category_doc)
    except Exception:
        pass
    return None


async def get_all_categories() -> List[MenuCategory]:
    """Get all menu categories sorted by sort_order"""
    if mongo.db is None:
        return []
    
    cursor = mongo.db.menu_categories.find().sort("sort_order", 1)
    categories = []
    async for category_doc in cursor:
        categories.append(MenuCategory.from_db(category_doc))
    return categories


async def create_category(category_data: MenuCategoryInDB) -> MenuCategory:
    """Create a new menu category"""
    if mongo.db is None:
        raise Exception("Database connection not available")
    
    category_dict = category_data.model_dump(by_alias=True, exclude={"id"})
    result = await mongo.db.menu_categories.insert_one(category_dict)
    
    created_category = await mongo.db.menu_categories.find_one({"_id": result.inserted_id})
    return MenuCategory.from_db(created_category)


async def update_category(category_id: str, update_data: dict) -> Optional[MenuCategory]:
    """Update a menu category"""
    if mongo.db is None:
        raise Exception("Database connection not available")
    
    try:
        # Remove None values
        update_dict = {k: v for k, v in update_data.items() if v is not None}
        
        if not update_dict:
            return await get_category_by_id(category_id)
        
        result = await mongo.db.menu_categories.update_one(
            {"_id": ObjectId(category_id)},
            {"$set": update_dict}
        )
        
        if result.modified_count == 0:
            return None
        
        return await get_category_by_id(category_id)
    except Exception:
        return None


async def delete_category(category_id: str) -> bool:
    """Delete a menu category"""
    if mongo.db is None:
        raise Exception("Database connection not available")
    
    try:
        result = await mongo.db.menu_categories.delete_one({"_id": ObjectId(category_id)})
        return result.deleted_count > 0
    except Exception:
        return False


async def category_exists(category_id: str) -> bool:
    """Check if a category exists"""
    if mongo.db is None:
        return False
    
    try:
        count = await mongo.db.menu_categories.count_documents({"_id": ObjectId(category_id)})
        return count > 0
    except Exception:
        return False

