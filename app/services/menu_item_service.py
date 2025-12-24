from typing import List, Optional
from fastapi import HTTPException, status
from app.models.menu import MenuItemCreate, MenuItemUpdate, MenuItem, MenuItemInDB
from app.repositories.menu_item_repo import (
    get_item_by_id,
    get_all_items,
    get_items_by_category,
    create_item,
    update_item,
    delete_item,
    item_exists
)
from app.repositories.menu_category_repo import category_exists


async def get_items(include_inactive: bool = False) -> List[MenuItem]:
    """Get all menu items"""
    return await get_all_items(include_inactive=include_inactive)


async def get_item(item_id: str) -> MenuItem:
    """Get a menu item by ID"""
    item = await get_item_by_id(item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu item not found"
        )
    return item


async def create_item_service(item_data: MenuItemCreate) -> MenuItem:
    """Create a new menu item"""
    # Validate category exists
    if not await category_exists(item_data.category_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    item_in_db = MenuItemInDB(**item_data.model_dump())
    return await create_item(item_in_db)


async def update_item_service(item_id: str, item_data: MenuItemUpdate) -> MenuItem:
    """Update a menu item"""
    if not await item_exists(item_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu item not found"
        )
    
    # Validate category exists if being updated
    if item_data.category_id and not await category_exists(item_data.category_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    update_dict = item_data.model_dump(exclude_unset=True)
    updated_item = await update_item(item_id, update_dict)
    
    if not updated_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu item not found"
        )
    
    return updated_item


async def delete_item_service(item_id: str) -> bool:
    """Delete a menu item"""
    if not await item_exists(item_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu item not found"
        )
    
    return await delete_item(item_id)

