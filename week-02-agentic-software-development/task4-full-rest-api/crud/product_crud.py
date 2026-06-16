from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
import models
from schemas.product_schemas import ProductCreate, ProductUpdate
from logger import get_logger

logger = get_logger(__name__)


def get_products(db: Session, skip: int = 0, limit: int = 100):
    logger.info(f"DB query: list products | skip={skip} limit={limit}")
    products = db.query(models.Product).offset(skip).limit(limit).all()
    logger.info(f"Returned {len(products)} products.")
    return products


def get_product(db: Session, product_code: str):
    logger.info(f"DB query: get product productCode={product_code}")
    product = (
        db.query(models.Product)
        .options(joinedload(models.Product.order_details))
        .filter(models.Product.productCode == product_code)
        .first()
    )
    if product is None:
        logger.warning(f"Product not found: productCode={product_code}")
    else:
        logger.info(f"Found product: {product.productName}")
    return product


def create_product(db: Session, data: ProductCreate):
    logger.info(f"DB query: create product productCode={data.productCode}")
    existing = db.query(models.Product).filter(
        models.Product.productCode == data.productCode
    ).first()
    if existing:
        logger.warning(
            f"Product already exists: productCode={data.productCode}")
        raise HTTPException(
            status_code=409, detail=f"Product '{data.productCode}' already exists.")

    db_product = models.Product(**data.model_dump())
    db.add(db_product)
    try:
        db.commit()
        db.refresh(db_product)
    except IntegrityError as e:
        db.rollback()
        logger.warning(f"FK constraint error creating product: {e}")
        raise HTTPException(
            status_code=422,
            detail=f"Invalid productLine '{data.productLine}'. It does not exist in productlines table."
        )
    logger.info(f"Product created: productCode={db_product.productCode}")
    return get_product(db, db_product.productCode)


def update_product(db: Session, product_code: str, updates: ProductUpdate):
    logger.info(f"DB query: update product productCode={product_code}")
    db_product = get_product(db, product_code)
    if db_product is None:
        logger.warning(f"Update failed — product {product_code} not found.")
        raise HTTPException(
            status_code=404, detail=f"Product '{product_code}' not found.")
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_product, field, value)
    try:
        db.commit()
        db.refresh(db_product)
    except IntegrityError as e:
        db.rollback()
        logger.warning(f"FK constraint error updating product: {e}")
        raise HTTPException(
            status_code=422, detail="Invalid foreign key value provided.")
    logger.info(f"Product {product_code} updated successfully.")
    return get_product(db, product_code)


def delete_product(db: Session, product_code: str):
    logger.info(f"DB query: delete product productCode={product_code}")
    db_product = get_product(db, product_code)
    if db_product is None:
        logger.warning(f"Delete failed — product {product_code} not found.")
        raise HTTPException(
            status_code=404, detail=f"Product '{product_code}' not found.")
    db.delete(db_product)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        logger.warning(
            f"FK constraint error deleting product {product_code}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete product '{product_code}' — it is still referenced by order details."
        )
    logger.info(f"Product {product_code} deleted.")
    return True


def get_product_with_orderdetails(db: Session, product_code: str):
    logger.info(
        f"DB query: get product with orderdetails productCode={product_code}")
    product = get_product(db, product_code)
    if product is None:
        raise HTTPException(
            status_code=404, detail=f"Product '{product_code}' not found.")
    logger.info(
        f"Found {len(product.order_details)} order details for product {product_code}.")
    return product
