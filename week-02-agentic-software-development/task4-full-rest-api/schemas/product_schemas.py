from pydantic import BaseModel, field_validator
from typing import Optional, List
from decimal import Decimal
from logger import get_logger

logger = get_logger(__name__)


class OrderDetailSimpleOut(BaseModel):
    orderNumber: int
    productCode: str
    quantityOrdered: int
    priceEach: Decimal
    orderLineNumber: int
    model_config = {"from_attributes": True}


class ProductCreate(BaseModel):
    productCode: str
    productName: str
    productLine: str
    productScale: str
    productVendor: str
    productDescription: str
    quantityInStock: int
    buyPrice: Decimal
    MSRP: Decimal

    @field_validator("quantityInStock")
    @classmethod
    def quantity_not_negative(cls, v: int) -> int:
        if v < 0:
            logger.warning(
                f"Validation error: quantityInStock={v} is negative.")
            raise ValueError("quantityInStock must be >= 0.")
        return v

    @field_validator("MSRP")
    @classmethod
    def msrp_not_negative(cls, v: Decimal) -> Decimal:
        if v < 0:
            logger.warning(f"Validation error: MSRP={v} is negative.")
            raise ValueError("MSRP must be >= 0.")
        return v

    @field_validator("buyPrice")
    @classmethod
    def buy_price_not_negative(cls, v: Decimal) -> Decimal:
        if v < 0:
            logger.warning(f"Validation error: buyPrice={v} is negative.")
            raise ValueError("buyPrice must be >= 0.")
        return v


class ProductOut(BaseModel):
    productCode: str
    productName: str
    productLine: str
    productScale: str
    productVendor: str
    productDescription: str
    quantityInStock: int
    buyPrice: Decimal
    MSRP: Decimal
    order_details: List[OrderDetailSimpleOut] = []
    model_config = {"from_attributes": True}


class ProductUpdate(BaseModel):
    productName: Optional[str] = None
    productLine: Optional[str] = None
    productScale: Optional[str] = None
    productVendor: Optional[str] = None
    productDescription: Optional[str] = None
    quantityInStock: Optional[int] = None
    buyPrice: Optional[Decimal] = None
    MSRP: Optional[Decimal] = None
