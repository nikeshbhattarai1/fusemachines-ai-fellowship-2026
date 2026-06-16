from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
import models
from schemas.orderdetail_schemas import OrderDetailCreate, OrderDetailUpdate
from logger import get_logger

logger = get_logger(__name__)


def get_orderdetails(db: Session, skip: int = 0, limit: int = 100):
    logger.info(f"DB query: list orderdetails | skip={skip} limit={limit}")
    details = db.query(models.OrderDetail).offset(skip).limit(limit).all()
    logger.info(f"Returned {len(details)} order details.")
    return details


def get_orderdetail(db: Session, order_number: int, product_code: str):
    logger.info(
        f"DB query: get orderdetail orderNumber={order_number} productCode={product_code}")
    detail = (
        db.query(models.OrderDetail)
        .filter(
            models.OrderDetail.orderNumber == order_number,
            models.OrderDetail.productCode == product_code,
        )
        .first()
    )
    if detail is None:
        logger.warning(
            f"OrderDetail not found: orderNumber={order_number} productCode={product_code}")
    else:
        logger.info(
            f"Found orderdetail: order={order_number} product={product_code}")
    return detail


def create_orderdetail(db: Session, data: OrderDetailCreate):
    logger.info(
        f"DB query: create orderdetail orderNumber={data.orderNumber} productCode={data.productCode}")
    existing = get_orderdetail(db, data.orderNumber, data.productCode)
    if existing:
        logger.warning(
            f"OrderDetail already exists: orderNumber={data.orderNumber} productCode={data.productCode}")
        raise HTTPException(
            status_code=409,
            detail=f"OrderDetail for order {data.orderNumber} and product '{data.productCode}' already exists."
        )
    db_detail = models.OrderDetail(**data.model_dump())
    db.add(db_detail)
    try:
        db.commit()
        db.refresh(db_detail)
    except IntegrityError as e:
        db.rollback()
        logger.warning(f"FK constraint error creating orderdetail: {e}")
        raise HTTPException(
            status_code=422,
            detail="Invalid orderNumber or productCode — referenced record does not exist."
        )
    logger.info(
        f"OrderDetail created: orderNumber={db_detail.orderNumber} productCode={db_detail.productCode}")
    return db_detail


def update_orderdetail(db: Session, order_number: int, product_code: str, updates: OrderDetailUpdate):
    logger.info(
        f"DB query: update orderdetail orderNumber={order_number} productCode={product_code}")
    db_detail = get_orderdetail(db, order_number, product_code)
    if db_detail is None:
        logger.warning(
            f"Update failed — orderdetail not found: order={order_number} product={product_code}")
        raise HTTPException(
            status_code=404,
            detail=f"OrderDetail for order {order_number} and product '{product_code}' not found."
        )
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_detail, field, value)
    db.commit()
    db.refresh(db_detail)
    logger.info(
        f"OrderDetail updated: order={order_number} product={product_code}")
    return db_detail


def delete_orderdetail(db: Session, order_number: int, product_code: str):
    logger.info(
        f"DB query: delete orderdetail orderNumber={order_number} productCode={product_code}")
    db_detail = get_orderdetail(db, order_number, product_code)
    if db_detail is None:
        logger.warning(
            f"Delete failed — orderdetail not found: order={order_number} product={product_code}")
        raise HTTPException(
            status_code=404,
            detail=f"OrderDetail for order {order_number} and product '{product_code}' not found."
        )
    db.delete(db_detail)
    db.commit()
    logger.info(
        f"OrderDetail deleted: order={order_number} product={product_code}")
    return True


def get_orderdetails_by_order(db: Session, order_number: int):
    logger.info(f"DB query: get orderdetails by orderNumber={order_number}")
    details = (
        db.query(models.OrderDetail)
        .filter(models.OrderDetail.orderNumber == order_number)
        .all()
    )
    logger.info(f"Found {len(details)} line items for order {order_number}.")
    return details


def get_orderdetails_by_product(db: Session, product_code: str):
    logger.info(f"DB query: get orderdetails by productCode={product_code}")
    details = (
        db.query(models.OrderDetail)
        .filter(models.OrderDetail.productCode == product_code)
        .all()
    )
    logger.info(
        f"Found {len(details)} order details for product {product_code}.")
    return details
