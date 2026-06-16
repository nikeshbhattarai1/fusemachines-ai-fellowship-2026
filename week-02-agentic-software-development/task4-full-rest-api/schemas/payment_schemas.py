from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import date
from decimal import Decimal
from logger import get_logger

logger = get_logger(__name__)


class PaymentCreate(BaseModel):
    customerNumber: int
    checkNumber: str
    paymentDate: date
    amount: Decimal

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            logger.warning(f"Validation error: amount={v} must be > 0.")
            raise ValueError("Payment amount must be greater than 0.")
        return v

    @field_validator("paymentDate")
    @classmethod
    def date_not_in_future(cls, v: date) -> date:
        if v > date.today():
            logger.warning(
                f"Validation error: paymentDate={v} is in the future.")
            raise ValueError("paymentDate cannot be in the future.")
        return v


class PaymentOut(BaseModel):
    customerNumber: int
    checkNumber: str
    paymentDate: date
    amount: Decimal
    model_config = {"from_attributes": True}


class PaymentUpdate(BaseModel):
    paymentDate: Optional[date] = None
    amount: Optional[Decimal] = None
