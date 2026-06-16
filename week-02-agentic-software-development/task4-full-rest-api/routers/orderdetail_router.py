from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from crud import orderdetail_crud
from schemas.orderdetail_schemas import OrderDetailCreate, OrderDetailUpdate, OrderDetailOut
from database import get_db
from logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["OrderDetails"])


@router.get("/", response_model=List[OrderDetailOut])
def list_orderdetails(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    logger.info(f"GET /orderdetails skip={skip} limit={limit}")
    details = orderdetail_crud.get_orderdetails(db, skip=skip, limit=limit)
    logger.info(f"GET /orderdetails — returned {len(details)} records.")
    return details


@router.get("/order/{order_number}", response_model=List[OrderDetailOut])
def get_orderdetails_by_order(order_number: int, db: Session = Depends(get_db)):
    logger.info(f"GET /orderdetails/order/{order_number}")
    details = orderdetail_crud.get_orderdetails_by_order(db, order_number)
    logger.info(
        f"GET /orderdetails/order/{order_number} — returned {len(details)} items.")
    return details


@router.get("/product/{product_code}", response_model=List[OrderDetailOut])
def get_orderdetails_by_product(product_code: str, db: Session = Depends(get_db)):
    logger.info(f"GET /orderdetails/product/{product_code}")
    details = orderdetail_crud.get_orderdetails_by_product(db, product_code)
    logger.info(
        f"GET /orderdetails/product/{product_code} — returned {len(details)} items.")
    return details


@router.get("/{order_number}/{product_code}", response_model=OrderDetailOut)
def get_orderdetail(order_number: int, product_code: str, db: Session = Depends(get_db)):
    logger.info(f"GET /orderdetails/{order_number}/{product_code}")
    detail = orderdetail_crud.get_orderdetail(db, order_number, product_code)
    if not detail:
        logger.warning(
            f"GET /orderdetails/{order_number}/{product_code} — 404 not found.")
        from fastapi import HTTPException
        raise HTTPException(
            status_code=404,
            detail=f"OrderDetail for order {order_number} and product '{product_code}' not found."
        )
    return detail


@router.post("/", response_model=OrderDetailOut, status_code=201)
def create_orderdetail(data: OrderDetailCreate, db: Session = Depends(get_db)):
    logger.info(
        f"POST /orderdetails orderNumber={data.orderNumber} productCode={data.productCode}")
    result = orderdetail_crud.create_orderdetail(db, data)
    logger.info(
        f"POST /orderdetails — created order={result.orderNumber} product={result.productCode}")
    return result


@router.put("/{order_number}/{product_code}", response_model=OrderDetailOut)
def update_orderdetail(order_number: int, product_code: str, updates: OrderDetailUpdate, db: Session = Depends(get_db)):
    logger.info(f"PUT /orderdetails/{order_number}/{product_code}")
    result = orderdetail_crud.update_orderdetail(
        db, order_number, product_code, updates)
    logger.info(
        f"PUT /orderdetails/{order_number}/{product_code} — updated successfully.")
    return result


@router.delete("/{order_number}/{product_code}", status_code=204)
def delete_orderdetail(order_number: int, product_code: str, db: Session = Depends(get_db)):
    logger.info(f"DELETE /orderdetails/{order_number}/{product_code}")
    orderdetail_crud.delete_orderdetail(db, order_number, product_code)
    logger.info(
        f"DELETE /orderdetails/{order_number}/{product_code} — deleted successfully.")
