from typing import List
from app.models.menu import MenuResponse, MenuCategoryWithItems, MenuItem
from app.repositories.menu_category_repo import get_all_categories
from app.repositories.menu_item_repo import get_items_by_category


async def get_menu() -> MenuResponse:
    """Get full menu with categories and items grouped"""
    categories = await get_all_categories()
    
    categories_with_items = []
    for category in categories:
        items = await get_items_by_category(category.id, include_inactive=False)
        category_with_items = MenuCategoryWithItems(
            id=category.id,
            name=category.name,
            sort_order=category.sort_order,
            created_at=category.created_at,
            items=items
        )
        categories_with_items.append(category_with_items)
    
    return MenuResponse(categories=categories_with_items)

