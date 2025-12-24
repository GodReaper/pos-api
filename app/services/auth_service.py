from datetime import timedelta
from typing import Optional
from fastapi import HTTPException, status
from app.core.security import hash_password, verify_password, create_access_token
from app.repositories.user_repo import (
    get_user_by_username,
    create_user,
    user_exists,
    admin_exists
)
from app.models.user import UserInDB, UserCreate, User
from app.core.config import settings


async def authenticate_user(username: str, password: str) -> Optional[User]:
    """Authenticate a user with username and password"""
    user = await get_user_by_username(username)
    
    if not user:
        return None
    
    # Get the full user document with password hash
    from app.db import mongo
    if mongo.db is None:
        return None
    
    user_doc = await mongo.db.users.find_one({"username": username})
    if not user_doc:
        return None
    
    if not verify_password(password, user_doc["password_hash"]):
        return None
    
    return user


async def login_user(username: str, password: str) -> dict:
    """Login a user and return access token"""
    user = await authenticate_user(username, password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


async def seed_admin(username: str, password: str) -> User:
    """Seed the first admin user"""
    # Check if admin already exists
    if await admin_exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Admin user already exists"
        )
    
    # Check if username already exists
    if await user_exists(username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists"
        )
    
    # Create admin user
    password_hash = hash_password(password)
    user_data = UserInDB(
        username=username,
        password_hash=password_hash,
        role="admin",
        is_active=True
    )
    
    admin_user = await create_user(user_data)
    return admin_user


async def create_biller(username: str, password: str) -> User:
    """Create a new biller user"""
    # Check if username already exists
    if await user_exists(username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists"
        )
    
    # Create biller user
    password_hash = hash_password(password)
    user_data = UserInDB(
        username=username,
        password_hash=password_hash,
        role="biller",
        is_active=True
    )
    
    biller_user = await create_user(user_data)
    return biller_user
