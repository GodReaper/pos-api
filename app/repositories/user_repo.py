from typing import Optional
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

