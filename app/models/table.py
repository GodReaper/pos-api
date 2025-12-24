from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from bson import ObjectId
from app.models.user import PyObjectId


class Position(BaseModel):
    """Table position model"""
    x: float = Field(..., description="X coordinate")
    y: float = Field(..., description="Y coordinate")


class TableBase(BaseModel):
    """Base table model"""
    area_id: str = Field(..., description="Area ID")
    name: str = Field(..., min_length=1, max_length=100)
    capacity: Optional[int] = Field(None, gt=0, description="Table capacity")
    position: Optional[Position] = Field(None, description="Table position coordinates")
    status: str = Field(default="available", pattern="^(available|occupied|reserved|out_of_order)$")
    current_order_id: Optional[str] = Field(None, description="Current order ID if occupied")


class TableCreate(BaseModel):
    """Table creation model (area_id comes from URL path)"""
    name: str = Field(..., min_length=1, max_length=100)
    capacity: Optional[int] = Field(None, gt=0, description="Table capacity")
    position: Optional[Position] = Field(None, description="Table position coordinates")
    status: str = Field(default="available", pattern="^(available|occupied|reserved|out_of_order)$")
    current_order_id: Optional[str] = Field(None, description="Current order ID if occupied")


class TableUpdate(BaseModel):
    """Table update model"""
    area_id: Optional[str] = None
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    capacity: Optional[int] = Field(None, gt=0)
    position: Optional[Position] = None
    status: Optional[str] = Field(None, pattern="^(available|occupied|reserved|out_of_order)$")
    current_order_id: Optional[str] = None


class TableInDB(TableBase):
    """Table model as stored in database"""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


class Table(TableBase):
    """Table model for API responses"""
    id: str
    updated_at: datetime

    @classmethod
    def from_db(cls, db_table: dict) -> "Table":
        """Create Table from database document"""
        return cls(
            id=str(db_table["_id"]),
            area_id=str(db_table["area_id"]),
            name=db_table["name"],
            capacity=db_table.get("capacity"),
            position=Position(**db_table["position"]) if db_table.get("position") else None,
            status=db_table.get("status", "available"),
            current_order_id=str(db_table["current_order_id"]) if db_table.get("current_order_id") else None,
            updated_at=db_table.get("updated_at", db_table.get("created_at", datetime.utcnow()))
        )

