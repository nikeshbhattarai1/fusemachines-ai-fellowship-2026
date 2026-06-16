from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from crud import productline_crud
from schemas.productline_schemas import ProductLineCreate, ProductLineUpdate, ProductLineOut
from database import get_db
from logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["ProductLines"])


@router.get("/", response_model=List[ProductLineOut])
def list_productlines(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    logger.info(f"GET /productlines skip={skip} limit={limit}")
    lines = productline_crud.get_productlines(db, skip=skip, limit=limit)
    logger.info(f"GET /productlines — returned {len(lines)} records.")
    return lines


@router.get("/{product_line}/products", response_model=ProductLineOut)
def get_productline_with_products(product_line: str, db: Session = Depends(get_db)):
    logger.info(f"GET /productlines/{product_line}/products")
    result = productline_crud.get_productline_with_products(db, product_line)
    logger.info(
        f"GET /productlines/{product_line}/products — returned {len(result.products)} products.")
    return result


@router.get("/{product_line}", response_model=ProductLineOut)
def get_productline(product_line: str, db: Session = Depends(get_db)):
    logger.info(f"GET /productlines/{product_line}")
    line = productline_crud.get_productline(db, product_line)
    if not line:
        logger.warning(f"GET /productlines/{product_line} — 404 not found.")
        raise HTTPException(
            status_code=404, detail=f"ProductLine '{product_line}' not found.")
    return line


@router.post("/", response_model=ProductLineOut, status_code=201)
def create_productline(data: ProductLineCreate, db: Session = Depends(get_db)):
    logger.info(f"POST /productlines productLine={data.productLine}")
    result = productline_crud.create_productline(db, data)
    logger.info(
        f"POST /productlines — created productLine={result.productLine}")
    return result


@router.put("/{product_line}", response_model=ProductLineOut)
def update_productline(product_line: str, updates: ProductLineUpdate, db: Session = Depends(get_db)):
    logger.info(f"PUT /productlines/{product_line}")
    result = productline_crud.update_productline(db, product_line, updates)
    logger.info(f"PUT /productlines/{product_line} — updated successfully.")
    return result


@router.delete("/{product_line}", status_code=204)
def delete_productline(product_line: str, db: Session = Depends(get_db)):
    logger.info(f"DELETE /productlines/{product_line}")
    productline_crud.delete_productline(db, product_line)
    logger.info(f"DELETE /productlines/{product_line} — deleted successfully.")
