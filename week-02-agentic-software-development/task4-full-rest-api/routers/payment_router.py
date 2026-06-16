from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from crud import payment_crud
from schemas.payment_schemas import PaymentCreate, PaymentUpdate, PaymentOut
from database import get_db
from logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Payments"])


@router.get("/", response_model=List[PaymentOut])
def list_payments(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    logger.info(f"GET /payments skip={skip} limit={limit}")
    payments = payment_crud.get_payments(db, skip=skip, limit=limit)
    logger.info(f"GET /payments — returned {len(payments)} records.")
    return payments


@router.get("/customer/{customer_number}", response_model=List[PaymentOut])
def get_payments_by_customer(customer_number: int, db: Session = Depends(get_db)):
    logger.info(f"GET /payments/customer/{customer_number}")
    payments = payment_crud.get_payments_by_customer(db, customer_number)
    logger.info(
        f"GET /payments/customer/{customer_number} — returned {len(payments)} payments.")
    return payments


@router.get("/{customer_number}/{check_number}", response_model=PaymentOut)
def get_payment(customer_number: int, check_number: str, db: Session = Depends(get_db)):
    logger.info(f"GET /payments/{customer_number}/{check_number}")
    payment = payment_crud.get_payment(db, customer_number, check_number)
    if not payment:
        logger.warning(
            f"GET /payments/{customer_number}/{check_number} — 404 not found.")
        from fastapi import HTTPException
        raise HTTPException(
            status_code=404,
            detail=f"Payment with checkNumber '{check_number}' for customer {customer_number} not found."
        )
    return payment


@router.post("/", response_model=PaymentOut, status_code=201)
def create_payment(data: PaymentCreate, db: Session = Depends(get_db)):
    logger.info(
        f"POST /payments customerNumber={data.customerNumber} checkNumber={data.checkNumber}")
    result = payment_crud.create_payment(db, data)
    logger.info(
        f"POST /payments — created customer={result.customerNumber} check={result.checkNumber}")
    return result


@router.put("/{customer_number}/{check_number}", response_model=PaymentOut)
def update_payment(customer_number: int, check_number: str, updates: PaymentUpdate, db: Session = Depends(get_db)):
    logger.info(f"PUT /payments/{customer_number}/{check_number}")
    result = payment_crud.update_payment(
        db, customer_number, check_number, updates)
    logger.info(
        f"PUT /payments/{customer_number}/{check_number} — updated successfully.")
    return result


@router.delete("/{customer_number}/{check_number}", status_code=204)
def delete_payment(customer_number: int, check_number: str, db: Session = Depends(get_db)):
    logger.info(f"DELETE /payments/{customer_number}/{check_number}")
    payment_crud.delete_payment(db, customer_number, check_number)
    logger.info(
        f"DELETE /payments/{customer_number}/{check_number} — deleted successfully.")
