from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from crud import product_crud
from schemas.product_schemas import ProductCreate, ProductUpdate, ProductOut
from database import get_db
from logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Products"])


@router.get("/", response_model=List[ProductOut])
def list_products(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    logger.info(f"GET /products skip={skip} limit={limit}")
    products = product_crud.get_products(db, skip=skip, limit=limit)
    logger.info(f"GET /products — returned {len(products)} records.")
    return products


@router.get("/{product_code}/orderdetails", response_model=ProductOut)
def get_product_with_orderdetails(product_code: str, db: Session = Depends(get_db)):
    logger.info(f"GET /products/{product_code}/orderdetails")
    result = product_crud.get_product_with_orderdetails(db, product_code)
    logger.info(
        f"GET /products/{product_code}/orderdetails — returned {len(result.order_details)} items.")
    return result


@router.get("/{product_code}", response_model=ProductOut)
def get_product(product_code: str, db: Session = Depends(get_db)):
    logger.info(f"GET /products/{product_code}")
    product = product_crud.get_product(db, product_code)
    if not product:
        logger.warning(f"GET /products/{product_code} — 404 not found.")
        raise HTTPException(
            status_code=404, detail=f"Product '{product_code}' not found.")
    return product


@router.post("/", response_model=ProductOut, status_code=201)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    logger.info(f"POST /products productCode={product.productCode}")
    result = product_crud.create_product(db, product)
    logger.info(f"POST /products — created productCode={result.productCode}")
    return result


@router.put("/{product_code}", response_model=ProductOut)
def update_product(product_code: str, updates: ProductUpdate, db: Session = Depends(get_db)):
    logger.info(f"PUT /products/{product_code}")
    result = product_crud.update_product(db, product_code, updates)
    logger.info(f"PUT /products/{product_code} — updated successfully.")
    return result


@router.delete("/{product_code}", status_code=204)
def delete_product(product_code: str, db: Session = Depends(get_db)):
    logger.info(f"DELETE /products/{product_code}")
    product_crud.delete_product(db, product_code)
    logger.info(f"DELETE /products/{product_code} — deleted successfully.")
