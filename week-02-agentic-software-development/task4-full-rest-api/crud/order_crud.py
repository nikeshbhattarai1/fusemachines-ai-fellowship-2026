from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
import models
from schemas.order_schemas import OrderCreate, OrderUpdate
from logger import get_logger

logger = get_logger(__name__)


def get_orders(db: Session, skip: int = 0, limit: int = 100):
    logger.info(f"DB query: list orders | skip={skip} limit={limit}")
    orders = db.query(models.Order).offset(skip).limit(limit).all()
    logger.info(f"Returned {len(orders)} orders.")
    return orders


def get_order(db: Session, order_number: int):
    logger.info(f"DB query: get order orderNumber={order_number}")
    order = (
        db.query(models.Order)
        .options(joinedload(models.Order.order_details))
        .filter(models.Order.orderNumber == order_number)
        .first()
    )
    if order is None:
        logger.warning(f"Order not found: orderNumber={order_number}")
    else:
        logger.info(f"Found order: {order.orderNumber}, status={order.status}")
    return order


def create_order(db: Session, data: OrderCreate):
    logger.info(f"DB query: create order orderNumber={data.orderNumber}")
    existing = db.query(models.Order).filter(
        models.Order.orderNumber == data.orderNumber
    ).first()
    if existing:
        logger.warning(f"Order already exists: orderNumber={data.orderNumber}")
        raise HTTPException(
            status_code=409, detail=f"Order {data.orderNumber} already exists.")

    db_order = models.Order(**data.model_dump())
    db.add(db_order)
    try:
        db.commit()
        db.refresh(db_order)
    except IntegrityError as e:
        db.rollback()
        logger.warning(f"FK constraint error creating order: {e}")
        raise HTTPException(
            status_code=422,
            detail=f"Invalid customerNumber '{data.customerNumber}' — customer does not exist."
        )
    logger.info(f"Order created: orderNumber={db_order.orderNumber}")
    return get_order(db, db_order.orderNumber)


def update_order(db: Session, order_number: int, updates: OrderUpdate):
    logger.info(f"DB query: update order orderNumber={order_number}")
    db_order = get_order(db, order_number)
    if db_order is None:
        logger.warning(f"Update failed — order {order_number} not found.")
        raise HTTPException(
            status_code=404, detail=f"Order {order_number} not found.")
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_order, field, value)
    try:
        db.commit()
        db.refresh(db_order)
    except IntegrityError as e:
        db.rollback()
        logger.warning(f"FK constraint error updating order: {e}")
        raise HTTPException(
            status_code=422, detail="Invalid foreign key value provided.")
    logger.info(f"Order {order_number} updated successfully.")
    return get_order(db, order_number)


def delete_order(db: Session, order_number: int):
    logger.info(f"DB query: delete order orderNumber={order_number}")
    db_order = get_order(db, order_number)
    if db_order is None:
        logger.warning(f"Delete failed — order {order_number} not found.")
        raise HTTPException(
            status_code=404, detail=f"Order {order_number} not found.")
    db.delete(db_order)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        logger.warning(
            f"FK constraint error deleting order {order_number}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete order {order_number} — it still has order detail line items."
        )
    logger.info(f"Order {order_number} deleted.")
    return True


def get_order_with_orderdetails(db: Session, order_number: int):
    logger.info(
        f"DB query: get order with orderdetails orderNumber={order_number}")
    order = get_order(db, order_number)
    if order is None:
        raise HTTPException(
            status_code=404, detail=f"Order {order_number} not found.")
    logger.info(
        f"Found {len(order.order_details)} line items for order {order_number}.")
    return order


def get_orders_by_customer(db: Session, customer_number: int):
    logger.info(f"DB query: get orders by customerNumber={customer_number}")
    orders = (
        db.query(models.Order)
        .filter(models.Order.customerNumber == customer_number)
        .all()
    )
    logger.info(f"Found {len(orders)} orders for customer {customer_number}.")
    return orders
