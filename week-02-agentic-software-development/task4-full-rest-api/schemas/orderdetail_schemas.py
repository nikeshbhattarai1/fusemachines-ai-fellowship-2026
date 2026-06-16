from pydantic import BaseModel, field_validator
from typing import Optional
from decimal import Decimal
from logger import get_logger

logger = get_logger(__name__)


class OrderDetailCreate(BaseModel):
    orderNumber: int
    productCode: str
    quantityOrdered: int
    priceEach: Decimal
    orderLineNumber: int

    @field_validator("quantityOrdered")
    @classmethod
    def quantity_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            logger.warning(
                f"Validation error: quantityOrdered={v} must be > 0.")
            raise ValueError("quantityOrdered must be greater than 0.")
        return v

    @field_validator("priceEach")
    @classmethod
    def price_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            logger.warning(f"Validation error: priceEach={v} must be > 0.")
            raise ValueError("priceEach must be greater than 0.")
        return v

    @field_validator("orderLineNumber")
    @classmethod
    def line_number_in_smallint_range(cls, v: int) -> int:
        if v < 1 or v > 32767:
            logger.warning(
                f"Validation error: orderLineNumber={v} out of smallint range.")
            raise ValueError("orderLineNumber must be between 1 and 32767.")
        return v


class OrderDetailOut(BaseModel):
    orderNumber: int
    productCode: str
    quantityOrdered: int
    priceEach: Decimal
    orderLineNumber: int
    model_config = {"from_attributes": True}


class OrderDetailUpdate(BaseModel):
    quantityOrdered: Optional[int] = None
    priceEach: Optional[Decimal] = None
    orderLineNumber: Optional[int] = None
