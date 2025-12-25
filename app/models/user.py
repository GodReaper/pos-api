from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic v2"""
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        from pydantic_core import core_schema
        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=core_schema.union_schema([
                core_schema.is_instance_schema(ObjectId),
                core_schema.chain_schema([
                    core_schema.str_schema(),
                    core_schema.no_info_plain_validator_function(cls.validate),
                ])
            ]),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda x: str(x)
            ),
        )

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return v
        if isinstance(v, str):
            if ObjectId.is_valid(v):
                return ObjectId(v)
            raise ValueError("Invalid ObjectId")
        raise ValueError("Invalid ObjectId")


class UserBase(BaseModel):
    """Base user model"""
    username: str = Field(..., min_length=3, max_length=50)
    role: str = Field(..., pattern="^(admin|biller)$")
    is_active: bool = True
    report_username: Optional[str] = Field(None, description="Username whose reports this user can view")


class UserCreate(UserBase):
    """User creation model"""
    password: str = Field(..., min_length=6)
    report_username: Optional[str] = Field(None, description="Username whose reports this user can view")


class UserInDB(UserBase):
    """User model as stored in database"""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    password_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )


class User(UserBase):
    """User model for API responses"""
    id: str
    created_at: datetime

    @classmethod
    def from_db(cls, db_user: dict) -> "User":
        """Create User from database document"""
        return cls(
            id=str(db_user["_id"]),
            username=db_user["username"],
            role=db_user["role"],
            is_active=db_user["is_active"],
            created_at=db_user["created_at"],
            report_username=db_user.get("report_username")
        )


class UserLogin(BaseModel):
    """Login request model"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response model"""
    access_token: str
    token_type: str = "bearer"


class UserUpdate(BaseModel):
    """User update model"""
    report_username: Optional[str] = Field(None, description="Username whose reports this user can view")


class SeedAdminRequest(BaseModel):
    """Seed admin request model"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)

