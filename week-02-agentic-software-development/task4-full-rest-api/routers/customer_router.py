from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from crud import customer_crud
from schemas.customer_schemas import CustomerCreate, CustomerUpdate, CustomerOut
from database import get_db
from logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Customers"])


@router.get("/", response_model=List[CustomerOut])
def list_customers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    logger.info(f"GET /customers skip={skip} limit={limit}")
    customers = customer_crud.get_customers(db, skip=skip, limit=limit)
    logger.info(f"GET /customers returned {len(customers)} records.")
    return customers


@router.get("/{customer_number}", response_model=CustomerOut)
def get_customer(customer_number: int, db: Session = Depends(get_db)):
    logger.info(f"GET /customers/{customer_number}")
    customer = customer_crud.get_customer(db, customer_number)
    if not customer:
        logger.warning(f"GET /customers/{customer_number} — 404 not found.")
        raise HTTPException(status_code=404, detail="Customer not found.")
    return customer


@router.post("/", response_model=CustomerOut, status_code=201)
def create_customer(customer: CustomerCreate, db: Session = Depends(get_db)):
    logger.info(f"POST /customers name={customer.customerName}")
    result = customer_crud.create_customer(db, customer)
    logger.info(
        f"POST /customers — created customerNumber={result.customerNumber}")
    return result


@router.put("/{customer_number}", response_model=CustomerOut)
def update_customer(customer_number: int, updates: CustomerUpdate, db: Session = Depends(get_db)):
    logger.info(f"PUT /customers/{customer_number}")
    updated = customer_crud.update_customer(db, customer_number, updates)
    if not updated:
        logger.warning(f"PUT /customers/{customer_number} — 404 not found.")
        raise HTTPException(status_code=404, detail="Customer not found.")
    logger.info(f"PUT /customers/{customer_number} — updated successfully.")
    return updated


@router.delete("/{customer_number}", status_code=204)
def delete_customer(customer_number: int, db: Session = Depends(get_db)):
    logger.info(f"DELETE /customers/{customer_number}")
    success = customer_crud.delete_customer(db, customer_number)
    if not success:
        logger.warning(f"DELETE /customers/{customer_number} — 404 not found.")
        raise HTTPException(status_code=404, detail="Customer not found.")
    logger.info(f"DELETE /customers/{customer_number} — deleted successfully.")


@router.get("/{customer_number}/orders")
def get_customer_orders(customer_number: int, db: Session = Depends(get_db)):
    logger.info(f"GET /customers/{customer_number}/orders")
    orders = customer_crud.get_customer_orders(db, customer_number)
    logger.info(
        f"GET /customers/{customer_number}/orders — returned {len(orders)} orders.")
    return orders


@router.get("/{customer_number}/payments")
def get_customer_payments(customer_number: int, db: Session = Depends(get_db)):
    logger.info(f"GET /customers/{customer_number}/payments")
    payments = customer_crud.get_customer_payments(db, customer_number)
    logger.info(
        f"GET /customers/{customer_number}/payments — returned {len(payments)} payments.")
    return payments
