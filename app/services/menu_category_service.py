from typing import List, Optional
from fastapi import HTTPException, status
from app.models.menu import MenuCategoryCreate, MenuCategoryUpdate, MenuCategory, MenuCategoryInDB
from app.repositories.menu_category_repo import (
    get_category_by_id,
    get_all_categories,
    create_category,
    update_category,
    delete_category,
    category_exists
)


async def get_categories() -> List[MenuCategory]:
    """Get all menu categories"""
    return await get_all_categories()


async def get_category(category_id: str) -> MenuCategory:
    """Get a menu category by ID"""
    category = await get_category_by_id(category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu category not found"
        )
    return category


async def create_category_service(category_data: MenuCategoryCreate) -> MenuCategory:
    """Create a new menu category"""
    category_in_db = MenuCategoryInDB(**category_data.model_dump())
    return await create_category(category_in_db)


async def update_category_service(category_id: str, category_data: MenuCategoryUpdate) -> MenuCategory:
    """Update a menu category"""
    if not await category_exists(category_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu category not found"
        )
    
    update_dict = category_data.model_dump(exclude_unset=True)
    updated_category = await update_category(category_id, update_dict)
    
    if not updated_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu category not found"
        )
    
    return updated_category


async def delete_category_service(category_id: str) -> bool:
    """Delete a menu category"""
    if not await category_exists(category_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu category not found"
        )
    
    # Check if category has items
    from app.repositories.menu_item_repo import get_items_by_category
    items = await get_items_by_category(category_id, include_inactive=True)
    if items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete category with existing items. Please delete or move items first."
        )
    
    return await delete_category(category_id)

