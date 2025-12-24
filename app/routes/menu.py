from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.menu import (
    MenuCategory,
    MenuCategoryCreate,
    MenuCategoryUpdate,
    MenuItem,
    MenuItemCreate,
    MenuItemUpdate,
    MenuResponse
)
from app.services.menu_category_service import (
    get_categories,
    get_category,
    create_category_service,
    update_category_service,
    delete_category_service
)
from app.services.menu_item_service import (
    get_items,
    get_item,
    create_item_service,
    update_item_service,
    delete_item_service
)
from app.services.menu_service import get_menu
from app.core.rbac import require_admin

router = APIRouter(prefix="/menu", tags=["menu"])


# Admin endpoints for categories
@router.get("/admin/categories", response_model=List[MenuCategory], dependencies=[Depends(require_admin)])
async def list_categories():
    """Get all menu categories (admin only)"""
    return await get_categories()


@router.post("/admin/categories", response_model=MenuCategory, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
async def create_category(category_data: MenuCategoryCreate):
    """Create a new menu category (admin only)"""
    return await create_category_service(category_data)


@router.get("/admin/categories/{category_id}", response_model=MenuCategory, dependencies=[Depends(require_admin)])
async def get_category_by_id(category_id: str):
    """Get a menu category by ID (admin only)"""
    return await get_category(category_id)


@router.put("/admin/categories/{category_id}", response_model=MenuCategory, dependencies=[Depends(require_admin)])
async def update_category(category_id: str, category_data: MenuCategoryUpdate):
    """Update a menu category (admin only)"""
    return await update_category_service(category_id, category_data)


@router.delete("/admin/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
async def delete_category(category_id: str):
    """Delete a menu category (admin only)"""
    await delete_category_service(category_id)
    return None


# Admin endpoints for items
@router.get("/admin/items", response_model=List[MenuItem], dependencies=[Depends(require_admin)])
async def list_items():
    """Get all menu items (admin only)"""
    return await get_items(include_inactive=True)


@router.post("/admin/items", response_model=MenuItem, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
async def create_item(item_data: MenuItemCreate):
    """Create a new menu item (admin only)"""
    return await create_item_service(item_data)


@router.get("/admin/items/{item_id}", response_model=MenuItem, dependencies=[Depends(require_admin)])
async def get_item_by_id(item_id: str):
    """Get a menu item by ID (admin only)"""
    return await get_item(item_id)


@router.put("/admin/items/{item_id}", response_model=MenuItem, dependencies=[Depends(require_admin)])
async def update_item(item_id: str, item_data: MenuItemUpdate):
    """Update a menu item (admin only)"""
    return await update_item_service(item_id, item_data)


@router.delete("/admin/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
async def delete_item(item_id: str):
    """Delete a menu item (admin only)"""
    await delete_item_service(item_id)
    return None


# Public/biller read endpoint
@router.get("", response_model=MenuResponse)
async def get_public_menu():
    """Get full menu with categories and items grouped (public - no authentication required)"""
    return await get_menu()

