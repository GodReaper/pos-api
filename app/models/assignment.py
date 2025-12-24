from datetime import datetime
from typing import List
from pydantic import BaseModel, Field
from bson import ObjectId
from app.models.user import PyObjectId


class AssignmentBase(BaseModel):
    """Base assignment model"""
    admin_id: str = Field(..., description="Admin user ID who created the assignment")
    biller_id: str = Field(..., description="Biller user ID")
    area_ids: List[str] = Field(..., min_items=1, description="List of area IDs assigned to biller")


class AssignmentCreate(AssignmentBase):
    """Assignment creation model"""
    pass


class AssignmentUpdate(BaseModel):
    """Assignment update model"""
    area_ids: List[str] = Field(..., min_items=1, description="List of area IDs assigned to biller")


class AssignmentInDB(AssignmentBase):
    """Assignment model as stored in database"""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


class Assignment(AssignmentBase):
    """Assignment model for API responses"""
    id: str
    created_at: datetime

    @classmethod
    def from_db(cls, db_assignment: dict) -> "Assignment":
        """Create Assignment from database document"""
        return cls(
            id=str(db_assignment["_id"]),
            admin_id=str(db_assignment["admin_id"]),
            biller_id=str(db_assignment["biller_id"]),
            area_ids=[str(aid) for aid in db_assignment["area_ids"]],
            created_at=db_assignment["created_at"]
        )

