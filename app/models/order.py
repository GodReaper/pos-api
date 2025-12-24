from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from bson import ObjectId
from app.models.user import PyObjectId


class OrderItem(BaseModel):
    """Order item model"""
    item_id: str = Field(..., description="Menu item ID")
    name_snapshot: str = Field(..., description="Item name at time of order")
    price_snapshot: float = Field(..., gt=0, description="Item price at time of order")
    qty: int = Field(..., gt=0, description="Quantity")
    notes: Optional[str] = Field(None, description="Item notes")


class OrderTotals(BaseModel):
    """Order totals model"""
    sub_total: float = Field(default=0.0, ge=0, description="Subtotal before tax and discount")
    tax_total: float = Field(default=0.0, ge=0, description="Total tax")
    discount_total: float = Field(default=0.0, ge=0, description="Total discount")
    grand_total: float = Field(default=0.0, ge=0, description="Grand total")


class KOTPrint(BaseModel):
    """KOT (Kitchen Order Ticket) print record"""
    printed_at: datetime = Field(default_factory=datetime.utcnow)
    items_snapshot: List[OrderItem] = Field(..., description="Items snapshot at print time")


class BillPrint(BaseModel):
    """Bill print record"""
    printed_at: datetime = Field(default_factory=datetime.utcnow)
    totals_snapshot: OrderTotals = Field(..., description="Totals snapshot at print time")


class Payment(BaseModel):
    """Payment record"""
    amount: float = Field(..., gt=0, description="Payment amount")
    method: str = Field(..., description="Payment method (cash, card, etc.)")
    paid_at: datetime = Field(default_factory=datetime.utcnow)
    notes: Optional[str] = Field(None, description="Payment notes")


class OrderBase(BaseModel):
    """Base order model"""
    table_id: str = Field(..., description="Table ID")
    area_id: str = Field(..., description="Area ID")
    status: str = Field(
        default="open",
        pattern="^(open|kot_printed|billed|paid|closed)$",
        description="Order status"
    )
    items: List[OrderItem] = Field(default_factory=list, description="Order items")
    totals: OrderTotals = Field(default_factory=OrderTotals, description="Order totals")
    kot_prints: List[KOTPrint] = Field(default_factory=list, description="KOT print history")
    bill_prints: List[BillPrint] = Field(default_factory=list, description="Bill print history")
    payments: List[Payment] = Field(default_factory=list, description="Payment history")
    created_by: str = Field(..., description="User ID who created the order")


class OrderCreate(BaseModel):
    """Order creation model"""
    table_id: str = Field(..., description="Table ID")
    area_id: str = Field(..., description="Area ID")
    created_by: str = Field(..., description="User ID who created the order")


class OrderItemUpdate(BaseModel):
    """Order item update model"""
    item_id: str = Field(..., description="Menu item ID")
    qty_delta: int = Field(..., description="Quantity change (positive to add, negative to remove)")
    notes: Optional[str] = Field(None, description="Item notes")


class OrderInDB(OrderBase):
    """Order model as stored in database"""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


class Order(OrderBase):
    """Order model for API responses"""
    id: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_db(cls, db_order: dict) -> "Order":
        """Create Order from database document"""
        return cls(
            id=str(db_order["_id"]),
            table_id=str(db_order["table_id"]),
            area_id=str(db_order["area_id"]),
            status=db_order.get("status", "open"),
            items=[OrderItem(**item) for item in db_order.get("items", [])],
            totals=OrderTotals(**db_order.get("totals", {})),
            kot_prints=[KOTPrint(**kot) for kot in db_order.get("kot_prints", [])],
            bill_prints=[BillPrint(**bill) for bill in db_order.get("bill_prints", [])],
            payments=[Payment(**payment) for payment in db_order.get("payments", [])],
            created_by=str(db_order["created_by"]),
            created_at=db_order.get("created_at", datetime.utcnow()),
            updated_at=db_order.get("updated_at", datetime.utcnow())
        )


class OrderWithTable(Order):
    """Order with table information"""
    table_name: Optional[str] = Field(None, description="Table name")
    area_name: Optional[str] = Field(None, description="Area name")

