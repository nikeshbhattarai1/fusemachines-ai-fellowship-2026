from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from crud import order_crud
from schemas.order_schemas import OrderCreate, OrderUpdate, OrderOut
from database import get_db
from logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Orders"])


@router.get("/", response_model=List[OrderOut])
def list_orders(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    logger.info(f"GET /orders skip={skip} limit={limit}")
    orders = order_crud.get_orders(db, skip=skip, limit=limit)
    logger.info(f"GET /orders — returned {len(orders)} records.")
    return orders


@router.get("/customer/{customer_number}", response_model=List[OrderOut])
def get_orders_by_customer(customer_number: int, db: Session = Depends(get_db)):
    logger.info(f"GET /orders/customer/{customer_number}")
    orders = order_crud.get_orders_by_customer(db, customer_number)
    logger.info(
        f"GET /orders/customer/{customer_number} — returned {len(orders)} orders.")
    return orders


@router.get("/{order_number}/orderdetails", response_model=OrderOut)
def get_order_with_orderdetails(order_number: int, db: Session = Depends(get_db)):
    logger.info(f"GET /orders/{order_number}/orderdetails")
    result = order_crud.get_order_with_orderdetails(db, order_number)
    logger.info(
        f"GET /orders/{order_number}/orderdetails — returned {len(result.order_details)} items.")
    return result


@router.get("/{order_number}", response_model=OrderOut)
def get_order(order_number: int, db: Session = Depends(get_db)):
    logger.info(f"GET /orders/{order_number}")
    order = order_crud.get_order(db, order_number)
    if not order:
        logger.warning(f"GET /orders/{order_number} — 404 not found.")
        raise HTTPException(
            status_code=404, detail=f"Order {order_number} not found.")
    return order


@router.post("/", response_model=OrderOut, status_code=201)
def create_order(data: OrderCreate, db: Session = Depends(get_db)):
    logger.info(f"POST /orders orderNumber={data.orderNumber}")
    result = order_crud.create_order(db, data)
    logger.info(f"POST /orders — created orderNumber={result.orderNumber}")
    return result


@router.put("/{order_number}", response_model=OrderOut)
def update_order(order_number: int, updates: OrderUpdate, db: Session = Depends(get_db)):
    logger.info(f"PUT /orders/{order_number}")
    result = order_crud.update_order(db, order_number, updates)
    logger.info(f"PUT /orders/{order_number} — updated successfully.")
    return result


@router.delete("/{order_number}", status_code=204)
def delete_order(order_number: int, db: Session = Depends(get_db)):
    logger.info(f"DELETE /orders/{order_number}")
    order_crud.delete_order(db, order_number)
    logger.info(f"DELETE /orders/{order_number} — deleted successfully.")
