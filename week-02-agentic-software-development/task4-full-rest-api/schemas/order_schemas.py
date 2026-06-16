from pydantic import BaseModel, model_validator
from typing import Optional, List, Literal
from datetime import date
from decimal import Decimal
from logger import get_logger

logger = get_logger(__name__)

# Only these 6 status values are valid for this assignment
OrderStatus = Literal["Shipped", "Resolved",
                      "Cancelled", "On Hold", "Disputed", "In Process"]


class OrderDetailSimpleOut(BaseModel):
    orderNumber: int
    productCode: str
    quantityOrdered: int
    priceEach: Decimal
    orderLineNumber: int
    model_config = {"from_attributes": True}


class OrderCreate(BaseModel):
    orderNumber: int
    orderDate: date
    requiredDate: date
    shippedDate: Optional[date] = None
    status: OrderStatus
    comments: Optional[str] = None
    customerNumber: int

    @model_validator(mode="after")
    def required_date_after_order_date(self) -> "OrderCreate":
        if self.requiredDate <= self.orderDate:
            logger.warning(
                f"Validation error: requiredDate={self.requiredDate} "
                f"must be after orderDate={self.orderDate}."
            )
            raise ValueError("requiredDate must be after orderDate.")
        return self


class OrderOut(BaseModel):
    orderNumber: int
    orderDate: date
    requiredDate: date
    shippedDate: Optional[date] = None
    status: str
    comments: Optional[str] = None
    customerNumber: int
    order_details: List[OrderDetailSimpleOut] = []
    model_config = {"from_attributes": True}


class OrderUpdate(BaseModel):
    orderDate: Optional[date] = None
    requiredDate: Optional[date] = None
    shippedDate: Optional[date] = None
    status: Optional[OrderStatus] = None
    comments: Optional[str] = None
    customerNumber: Optional[int] = None
