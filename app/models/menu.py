from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from bson import ObjectId
from app.models.user import PyObjectId


class MenuCategoryBase(BaseModel):
    """Base menu category model"""
    name: str = Field(..., min_length=1, max_length=100)
    sort_order: int = Field(default=0, ge=0)


class MenuCategoryCreate(MenuCategoryBase):
    """Menu category creation model"""
    pass


class MenuCategoryUpdate(BaseModel):
    """Menu category update model"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    sort_order: Optional[int] = Field(None, ge=0)


class MenuCategoryInDB(MenuCategoryBase):
    """Menu category model as stored in database"""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


class MenuCategory(MenuCategoryBase):
    """Menu category model for API responses"""
    id: str
    created_at: datetime

    @classmethod
    def from_db(cls, db_category: dict) -> "MenuCategory":
        """Create MenuCategory from database document"""
        return cls(
            id=str(db_category["_id"]),
            name=db_category["name"],
            sort_order=db_category["sort_order"],
            created_at=db_category["created_at"]
        )


class MenuItemBase(BaseModel):
    """Base menu item model"""
    category_id: str = Field(..., description="Category ID")
    name: str = Field(..., min_length=1, max_length=100)
    price: float = Field(..., gt=0, description="Item price")
    is_active: bool = Field(default=True)


class MenuItemCreate(MenuItemBase):
    """Menu item creation model"""
    pass


class MenuItemUpdate(BaseModel):
    """Menu item update model"""
    category_id: Optional[str] = None
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    price: Optional[float] = Field(None, gt=0)
    is_active: Optional[bool] = None


class MenuItemInDB(MenuItemBase):
    """Menu item model as stored in database"""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


class MenuItem(MenuItemBase):
    """Menu item model for API responses"""
    id: str
    created_at: datetime

    @classmethod
    def from_db(cls, db_item: dict) -> "MenuItem":
        """Create MenuItem from database document"""
        return cls(
            id=str(db_item["_id"]),
            category_id=str(db_item["category_id"]),
            name=db_item["name"],
            price=db_item["price"],
            is_active=db_item["is_active"],
            created_at=db_item["created_at"]
        )


class MenuCategoryWithItems(MenuCategory):
    """Menu category with its items"""
    items: list[MenuItem] = Field(default_factory=list)


class MenuResponse(BaseModel):
    """Menu response model with categories and items grouped"""
    categories: list[MenuCategoryWithItems]

