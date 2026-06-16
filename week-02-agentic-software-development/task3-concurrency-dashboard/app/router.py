import asyncio
import time
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import app.crud as crud
from app.database import get_db, SessionLocal
from app.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["counts"])


def _run_count_in_thread(count_fn) -> int:
    db = SessionLocal()
    try:
        return count_fn(db)
    finally:
        db.close()


@router.get("/customers/count")
def customers_count(db: Session = Depends(get_db)):
    logger.info("GET /customers/count — request received")
    count = crud.get_customers_count(db)
    logger.info(f"GET /customers/count — response: {count}")
    return {"table": "customers", "count": count}


@router.get("/orders/count")
def orders_count(db: Session = Depends(get_db)):
    logger.info("GET /orders/count — request received")
    count = crud.get_orders_count(db)
    logger.info(f"GET /orders/count — response: {count}")
    return {"table": "orders", "count": count}


@router.get("/products/count")
def products_count(db: Session = Depends(get_db)):
    logger.info("GET /products/count — request received")
    count = crud.get_products_count(db)
    logger.info(f"GET /products/count — response: {count}")
    return {"table": "products", "count": count}


@router.get("/employees/count")
def employees_count(db: Session = Depends(get_db)):
    logger.info("GET /employees/count — request received")
    count = crud.get_employees_count(db)
    logger.info(f"GET /employees/count — response: {count}")
    return {"table": "employees", "count": count}


@router.get("/offices/count")
def offices_count(db: Session = Depends(get_db)):
    logger.info("GET /offices/count — request received")
    count = crud.get_offices_count(db)
    logger.info(f"GET /offices/count — response: {count}")
    return {"table": "offices", "count": count}


@router.get("/payments/count")
def payments_count(db: Session = Depends(get_db)):
    logger.info("GET /payments/count — request received")
    count = crud.get_payments_count(db)
    logger.info(f"GET /payments/count — response: {count}")
    return {"table": "payments", "count": count}


@router.get("/orderdetails/count")
def orderdetails_count(db: Session = Depends(get_db)):
    logger.info("GET /orderdetails/count — request received")
    count = crud.get_orderdetails_count(db)
    logger.info(f"GET /orderdetails/count — response: {count}")
    return {"table": "orderdetails", "count": count}


@router.get("/productlines/count")
def productlines_count(db: Session = Depends(get_db)):
    logger.info("GET /productlines/count — request received")
    count = crud.get_productlines_count(db)
    logger.info(f"GET /productlines/count — response: {count}")
    return {"table": "productlines", "count": count}


@router.get("/overall_counts")
async def overall_counts():
    logger.info("GET /overall_counts — starting 8 concurrent DB queries")
    start_time = time.perf_counter()

    (
        customers, orders, products, employees, 
        offices, payments, orderdetails, productlines,
    ) = await asyncio.gather(
        asyncio.to_thread(_run_count_in_thread, crud.get_customers_count),
        asyncio.to_thread(_run_count_in_thread, crud.get_orders_count),
        asyncio.to_thread(_run_count_in_thread, crud.get_products_count),
        asyncio.to_thread(_run_count_in_thread, crud.get_employees_count),
        asyncio.to_thread(_run_count_in_thread, crud.get_offices_count),
        asyncio.to_thread(_run_count_in_thread, crud.get_payments_count),
        asyncio.to_thread(_run_count_in_thread, crud.get_orderdetails_count),
        asyncio.to_thread(_run_count_in_thread, crud.get_productlines_count),
    )

    elapsed = time.perf_counter() - start_time
    logger.info(
        f"asyncio.gather() completed in {elapsed:.4f}s — "
        f"customers={customers}, orders={orders}, products={products}, "
        f"employees={employees}, offices={offices}, payments={payments}, "
        f"orderdetails={orderdetails}, productlines={productlines}"
    )

    return {
        "customers": customers,
        "orders": orders,
        "products": products,
        "employees": employees,
        "offices": offices,
        "payments": payments,
        "orderdetails": orderdetails,
        "productlines": productlines,
    }
