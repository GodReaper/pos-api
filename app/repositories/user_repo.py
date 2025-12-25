from typing import Optional, List
from datetime import datetime
from app.db import mongo
from app.models.user import UserInDB, User
from bson import ObjectId


async def get_user_by_username(username: str) -> Optional[User]:
    """Get a user by username"""
    if mongo.db is None:
        return None
    
    user_doc = await mongo.db.users.find_one({"username": username})
    if user_doc:
        return User.from_db(user_doc)
    return None


async def get_user_by_id(user_id: str) -> Optional[User]:
    """Get a user by ID"""
    if mongo.db is None:
        return None
    
    try:
        user_doc = await mongo.db.users.find_one({"_id": ObjectId(user_id)})
        if user_doc:
            return User.from_db(user_doc)
    except Exception:
        pass
    return None


async def create_user(user_data: UserInDB) -> User:
    """Create a new user"""
    if mongo.db is None:
        raise Exception("Database connection not available")
    
    user_dict = user_data.model_dump(by_alias=True, exclude={"id"})
    result = await mongo.db.users.insert_one(user_dict)
    
    created_user = await mongo.db.users.find_one({"_id": result.inserted_id})
    return User.from_db(created_user)


async def user_exists(username: str) -> bool:
    """Check if a user exists"""
    if mongo.db is None:
        return False
    
    count = await mongo.db.users.count_documents({"username": username})
    return count > 0


async def admin_exists() -> bool:
    """Check if an admin user exists"""
    if mongo.db is None:
        return False
    
    count = await mongo.db.users.count_documents({"role": "admin"})
    return count > 0


async def get_all_users() -> List[User]:
    """Get all users"""
    if mongo.db is None:
        return []
    
    cursor = mongo.db.users.find()
    users = []
    async for user_doc in cursor:
        users.append(User.from_db(user_doc))
    return users


async def update_user(user_id: str, update_data: dict) -> Optional[User]:
    """Update a user by ID"""
    if mongo.db is None:
        raise Exception("Database connection not available")
    
    try:
        # Separate fields to set and unset
        set_data = {}
        unset_data = {}
        
        for key, value in update_data.items():
            if value is None:
                unset_data[key] = ""
            else:
                set_data[key] = value
        
        update_op = {}
        if set_data:
            update_op["$set"] = set_data
        if unset_data:
            update_op["$unset"] = unset_data
        
        if not update_op:
            # No changes to make, return current user
            user_doc = await mongo.db.users.find_one({"_id": ObjectId(user_id)})
            if user_doc:
                return User.from_db(user_doc)
            return None
        
        result = await mongo.db.users.update_one(
            {"_id": ObjectId(user_id)},
            update_op
        )
        
        if result.modified_count > 0 or result.matched_count > 0:
            updated_user = await mongo.db.users.find_one({"_id": ObjectId(user_id)})
            if updated_user:
                return User.from_db(updated_user)
    except Exception:
        pass
    
    return None


async def update_user_by_username(username: str, update_data: dict) -> Optional[User]:
    """Update a user by username"""
    if mongo.db is None:
        raise Exception("Database connection not available")
    
    try:
        # Get user to find their ID
        user = await get_user_by_username(username)
        if not user:
            return None
        
        # Separate fields to set and unset
        set_data = {}
        unset_data = {}
        
        for key, value in update_data.items():
            if value is None:
                unset_data[key] = ""
            else:
                set_data[key] = value
        
        update_op = {}
        if set_data:
            update_op["$set"] = set_data
        if unset_data:
            update_op["$unset"] = unset_data
        
        if not update_op:
            # No changes to make, return current user
            return user
        
        result = await mongo.db.users.update_one(
            {"username": username},
            update_op
        )
        
        if result.modified_count > 0 or result.matched_count > 0:
            updated_user = await get_user_by_username(username)
            if updated_user:
                return updated_user
    except Exception:
        pass
    
    return None

