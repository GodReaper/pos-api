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
        pattern="^(open|kot_printed|billed|paid|closed|cancelled)$",
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
    cancelled_at: Optional[datetime] = Field(None, description="When the order was cancelled")
    cancelled_by_user_id: Optional[PyObjectId] = Field(
        None, description="User ID who cancelled the order"
    )
    cancelled_by_role: Optional[str] = Field(
        None, pattern="^(admin|biller)$", description="Role of user who cancelled the order"
    )
    cancel_reason: Optional[str] = Field(None, description="Reason for cancellation")

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
    cancelled_at: Optional[datetime] = None
    cancelled_by_user_id: Optional[str] = None
    cancelled_by_role: Optional[str] = None
    cancel_reason: Optional[str] = None

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
            updated_at=db_order.get("updated_at", datetime.utcnow()),
            cancelled_at=db_order.get("cancelled_at"),
            cancelled_by_user_id=(
                str(db_order["cancelled_by_user_id"])
                if db_order.get("cancelled_by_user_id")
                else None
            ),
            cancelled_by_role=db_order.get("cancelled_by_role"),
            cancel_reason=db_order.get("cancel_reason"),
        )


class OrderWithTable(Order):
    """Order with table information"""
    table_name: Optional[str] = Field(None, description="Table name")
    area_name: Optional[str] = Field(None, description="Area name")


class OrderItemPreview(BaseModel):
    """Lightweight item preview for order listings"""
    name: str
    qty: int
    price: float


class OrderListItem(BaseModel):
    """Order list item projection for listings"""
    id: str = Field(..., description="Order ID")
    status: str = Field(..., description="Order status")
    area_id: str = Field(..., description="Area ID")
    table_id: str = Field(..., description="Table ID")
    table_name: Optional[str] = Field(None, description="Table name")
    area_name: Optional[str] = Field(None, description="Area name")
    created_by: str = Field(..., description="User ID who created the order")
    created_by_username: Optional[str] = Field(None, description="Username of creator")
    created_at: datetime
    updated_at: datetime
    grand_total: float = Field(..., description="Grand total from totals")
    items_count: int = Field(..., description="Total number of items (sum of qty)")
    items_preview: List[OrderItemPreview] = Field(
        default_factory=list,
        description="First 3 item previews (name + qty)"
    )
