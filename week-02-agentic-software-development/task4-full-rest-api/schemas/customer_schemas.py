from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import date
from decimal import Decimal
from logger import get_logger

logger = get_logger(__name__)


class OrderOut(BaseModel):
    orderNumber: int
    orderDate: date
    requiredDate: date
    shippedDate: Optional[date] = None
    status: str
    comments: Optional[str] = None
    customerNumber: int
    model_config = {"from_attributes": True}


class PaymentOut(BaseModel):
    customerNumber: int
    checkNumber: str
    paymentDate: date
    amount: Decimal
    model_config = {"from_attributes": True}


class CustomerCreate(BaseModel):
    customerName: str
    contactLastName: str
    contactFirstName: str
    phone: str
    addressLine1: str
    addressLine2: Optional[str] = None
    city: str
    state: Optional[str] = None
    postalCode: Optional[str] = None
    country: str
    salesRepEmployeeNumber: Optional[int] = None
    creditLimit: Optional[Decimal] = None

    @field_validator(
        "customerName", "contactLastName", "contactFirstName",
        "phone", "addressLine1", "city", "country"
    )
    @classmethod
    def must_not_be_blank(cls, v: str) -> str:
        if not v or not v.strip():
            logger.warning("Validation error: required field is blank.")
            raise ValueError("Field must not be blank.")
        return v


class CustomerUpdate(BaseModel):
    customerName: Optional[str] = None
    contactLastName: Optional[str] = None
    contactFirstName: Optional[str] = None
    phone: Optional[str] = None
    addressLine1: Optional[str] = None
    addressLine2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postalCode: Optional[str] = None
    country: Optional[str] = None
    salesRepEmployeeNumber: Optional[int] = None
    creditLimit: Optional[Decimal] = None


class CustomerOut(BaseModel):
    customerNumber: int
    customerName: str
    contactLastName: str
    contactFirstName: str
    phone: str
    addressLine1: str
    addressLine2: Optional[str] = None
    city: str
    state: Optional[str] = None
    postalCode: Optional[str] = None
    country: str
    salesRepEmployeeNumber: Optional[int] = None
    creditLimit: Optional[Decimal] = None
    orders: List[OrderOut] = []
    payments: List[PaymentOut] = []
    model_config = {"from_attributes": True}
