from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

import app.crud as crud
import app.schemas as schemas
from app.database import get_db
from app.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["customers"])


@router.get("/", response_model=List[schemas.CustomerOut])
def list_customers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    logger.info(f"GET /customers skip={skip} limit={limit}")
    return crud.get_customers(db, skip=skip, limit=limit)


@router.get("/{customer_number}", response_model=schemas.CustomerOut)
def get_customer(customer_number: int, db: Session = Depends(get_db)):
    logger.info(f"GET /customers/{customer_number}")
    customer = crud.get_customer(db, customer_number)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.post("/", response_model=schemas.CustomerOut, status_code=201)
def create_customer(customer: schemas.CustomerCreate, db: Session = Depends(get_db)):
    logger.info(f"POST /customers name={customer.customerName}")
    return crud.create_customer(db, customer)


@router.put("/{customer_number}", response_model=schemas.CustomerOut)
def update_customer(
    customer_number: int,
    updates: schemas.CustomerUpdate,
    db: Session = Depends(get_db),
):
    logger.info(f"PUT /customers/{customer_number}")
    updated = crud.update_customer(db, customer_number, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Customer not found")
    return updated


@router.delete("/{customer_number}", status_code=204)
def delete_customer(customer_number: int, db: Session = Depends(get_db)):
    logger.info(f"DELETE /customers/{customer_number}")
    success = crud.delete_customer(db, customer_number)
    if not success:
        raise HTTPException(status_code=404, detail="Customer not found")


@router.get("/{customer_number}/orders", response_model=List[schemas.OrderOut])
def get_customer_orders(customer_number: int, db: Session = Depends(get_db)):
    logger.info(f"GET /customers/{customer_number}/orders")
    return crud.get_customer_orders(db, customer_number)


@router.get("/{customer_number}/payments", response_model=List[schemas.PaymentOut])
def get_customer_payments(customer_number: int, db: Session = Depends(get_db)):
    logger.info(f"GET /customers/{customer_number}/payments")
    return crud.get_customer_payments(db, customer_number)
