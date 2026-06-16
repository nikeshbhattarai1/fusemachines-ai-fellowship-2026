from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
import models
from schemas.productline_schemas import ProductLineCreate, ProductLineUpdate
from logger import get_logger

logger = get_logger(__name__)


def get_productlines(db: Session, skip: int = 0, limit: int = 100):
    logger.info(f"DB query: list productlines | skip={skip} limit={limit}")
    lines = db.query(models.ProductLine).offset(skip).limit(limit).all()
    logger.info(f"Returned {len(lines)} product lines.")
    return lines


def get_productline(db: Session, product_line: str):
    logger.info(f"DB query: get productline productLine={product_line}")
    line = (
        db.query(models.ProductLine)
        .options(joinedload(models.ProductLine.products))
        .filter(models.ProductLine.productLine == product_line)
        .first()
    )
    if line is None:
        logger.warning(f"ProductLine not found: productLine={product_line}")
    else:
        logger.info(f"Found productLine: {line.productLine}")
    return line


def create_productline(db: Session, data: ProductLineCreate):
    logger.info(f"DB query: create productline productLine={data.productLine}")
    existing = db.query(models.ProductLine).filter(
        models.ProductLine.productLine == data.productLine
    ).first()
    if existing:
        logger.warning(f"ProductLine already exists: {data.productLine}")
        raise HTTPException(
            status_code=409, detail=f"ProductLine '{data.productLine}' already exists.")

    db_line = models.ProductLine(**data.model_dump())
    db.add(db_line)
    db.commit()
    db.refresh(db_line)
    logger.info(f"ProductLine created: {db_line.productLine}")
    return get_productline(db, db_line.productLine)


def update_productline(db: Session, product_line: str, updates: ProductLineUpdate):
    logger.info(f"DB query: update productline productLine={product_line}")
    db_line = get_productline(db, product_line)
    if db_line is None:
        logger.warning(
            f"Update failed — productLine {product_line} not found.")
        raise HTTPException(
            status_code=404, detail=f"ProductLine '{product_line}' not found.")
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_line, field, value)
    db.commit()
    db.refresh(db_line)
    logger.info(f"ProductLine {product_line} updated successfully.")
    return get_productline(db, product_line)


def delete_productline(db: Session, product_line: str):
    logger.info(f"DB query: delete productline productLine={product_line}")
    db_line = get_productline(db, product_line)
    if db_line is None:
        logger.warning(
            f"Delete failed — productLine {product_line} not found.")
        raise HTTPException(
            status_code=404, detail=f"ProductLine '{product_line}' not found.")
    db.delete(db_line)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        logger.warning(
            f"FK constraint error deleting productLine {product_line}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete '{product_line}' — products still reference this product line."
        )
    logger.info(f"ProductLine {product_line} deleted.")
    return True


def get_productline_with_products(db: Session, product_line: str):
    logger.info(
        f"DB query: get productline with products productLine={product_line}")
    line = get_productline(db, product_line)
    if line is None:
        raise HTTPException(
            status_code=404, detail=f"ProductLine '{product_line}' not found.")
    logger.info(
        f"Found {len(line.products)} products for productLine {product_line}.")
    return line
