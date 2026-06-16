from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
import models
from schemas.payment_schemas import PaymentCreate, PaymentUpdate
from logger import get_logger

logger = get_logger(__name__)


def get_payments(db: Session, skip: int = 0, limit: int = 100):
    logger.info(f"DB query: list payments | skip={skip} limit={limit}")
    payments = db.query(models.Payment).offset(skip).limit(limit).all()
    logger.info(f"Returned {len(payments)} payments.")
    return payments


def get_payment(db: Session, customer_number: int, check_number: str):
    logger.info(
        f"DB query: get payment customerNumber={customer_number} checkNumber={check_number}")
    payment = (
        db.query(models.Payment)
        .filter(
            models.Payment.customerNumber == customer_number,
            models.Payment.checkNumber == check_number,
        )
        .first()
    )
    if payment is None:
        logger.warning(
            f"Payment not found: customerNumber={customer_number} checkNumber={check_number}")
    else:
        logger.info(
            f"Found payment: customer={customer_number} check={check_number} amount={payment.amount}")
    return payment


def create_payment(db: Session, data: PaymentCreate):
    logger.info(
        f"DB query: create payment customerNumber={data.customerNumber} checkNumber={data.checkNumber}")
    existing = get_payment(db, data.customerNumber, data.checkNumber)
    if existing:
        logger.warning(
            f"Payment already exists: customerNumber={data.customerNumber} checkNumber={data.checkNumber}")
        raise HTTPException(
            status_code=409,
            detail=f"Payment with checkNumber '{data.checkNumber}' for customer {data.customerNumber} already exists."
        )
    db_payment = models.Payment(**data.model_dump())
    db.add(db_payment)
    try:
        db.commit()
        db.refresh(db_payment)
    except IntegrityError as e:
        db.rollback()
        logger.warning(f"FK constraint error creating payment: {e}")
        raise HTTPException(
            status_code=422,
            detail=f"Invalid customerNumber '{data.customerNumber}' — customer does not exist."
        )
    logger.info(
        f"Payment created: customerNumber={db_payment.customerNumber} checkNumber={db_payment.checkNumber}")
    return db_payment


def update_payment(db: Session, customer_number: int, check_number: str, updates: PaymentUpdate):
    logger.info(
        f"DB query: update payment customerNumber={customer_number} checkNumber={check_number}")
    db_payment = get_payment(db, customer_number, check_number)
    if db_payment is None:
        logger.warning(
            f"Update failed — payment not found: customer={customer_number} check={check_number}")
        raise HTTPException(
            status_code=404,
            detail=f"Payment with checkNumber '{check_number}' for customer {customer_number} not found."
        )
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_payment, field, value)
    db.commit()
    db.refresh(db_payment)
    logger.info(
        f"Payment updated: customer={customer_number} check={check_number}")
    return db_payment


def delete_payment(db: Session, customer_number: int, check_number: str):
    logger.info(
        f"DB query: delete payment customerNumber={customer_number} checkNumber={check_number}")
    db_payment = get_payment(db, customer_number, check_number)
    if db_payment is None:
        logger.warning(
            f"Delete failed — payment not found: customer={customer_number} check={check_number}")
        raise HTTPException(
            status_code=404,
            detail=f"Payment with checkNumber '{check_number}' for customer {customer_number} not found."
        )
    db.delete(db_payment)
    db.commit()
    logger.info(
        f"Payment deleted: customer={customer_number} check={check_number}")
    return True


def get_payments_by_customer(db: Session, customer_number: int):
    logger.info(f"DB query: get payments by customerNumber={customer_number}")
    payments = (
        db.query(models.Payment)
        .filter(models.Payment.customerNumber == customer_number)
        .all()
    )
    logger.info(
        f"Found {len(payments)} payments for customer {customer_number}.")
    return payments
