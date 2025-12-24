from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from bson import ObjectId
from app.models.user import PyObjectId


class AreaBase(BaseModel):
    """Base area model"""
    name: str = Field(..., min_length=1, max_length=100)
    sort_order: int = Field(default=0, ge=0)


class AreaCreate(AreaBase):
    """Area creation model"""
    pass


class AreaUpdate(BaseModel):
    """Area update model"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    sort_order: Optional[int] = Field(None, ge=0)


class AreaInDB(AreaBase):
    """Area model as stored in database"""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


class Area(AreaBase):
    """Area model for API responses"""
    id: str
    created_at: datetime

    @classmethod
    def from_db(cls, db_area: dict) -> "Area":
        """Create Area from database document"""
        return cls(
            id=str(db_area["_id"]),
            name=db_area["name"],
            sort_order=db_area["sort_order"],
            created_at=db_area["created_at"]
        )

