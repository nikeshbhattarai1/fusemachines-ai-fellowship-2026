from sqlalchemy.orm import Session
from sqlalchemy import func
import app.models as models
from app.logger import get_logger

logger = get_logger(__name__)


def get_customers_count(db: Session) -> int:
    logger.info("DB query: COUNT customers")
    try:
        count = db.query(func.count(
            models.Customer.customerNumber)).scalar() or 0
        logger.info(f"customers count = {count}")
        return count
    except Exception as e:
        logger.error(f"Error counting customers: {e}")
        return 0


def get_orders_count(db: Session) -> int:
    logger.info("DB query: COUNT orders")
    try:
        count = db.query(func.count(models.Order.orderNumber)).scalar() or 0
        logger.info(f"orders count = {count}")
        return count
    except Exception as e:
        logger.error(f"Error counting orders: {e}")
        return 0


def get_products_count(db: Session) -> int:
    logger.info("DB query: COUNT products")
    try:
        count = db.query(func.count(models.Product.productCode)).scalar() or 0
        logger.info(f"products count = {count}")
        return count
    except Exception as e:
        logger.error(f"Error counting products: {e}")
        return 0


def get_employees_count(db: Session) -> int:
    logger.info("DB query: COUNT employees")
    try:
        count = db.query(func.count(
            models.Employee.employeeNumber)).scalar() or 0
        logger.info(f"employees count = {count}")
        return count
    except Exception as e:
        logger.error(f"Error counting employees: {e}")
        return 0


def get_offices_count(db: Session) -> int:
    logger.info("DB query: COUNT offices")
    try:
        count = db.query(func.count(models.Office.officeCode)).scalar() or 0
        logger.info(f"offices count = {count}")
        return count
    except Exception as e:
        logger.error(f"Error counting offices: {e}")
        return 0


def get_payments_count(db: Session) -> int:
    logger.info("DB query: COUNT payments")
    try:
        count = db.query(func.count(models.Payment.checkNumber)).scalar() or 0
        logger.info(f"payments count = {count}")
        return count
    except Exception as e:
        logger.error(f"Error counting payments: {e}")
        return 0


def get_orderdetails_count(db: Session) -> int:
    logger.info("DB query: COUNT orderdetails")
    try:
        count = db.query(func.count(
            models.OrderDetail.orderNumber)).scalar() or 0
        logger.info(f"orderdetails count = {count}")
        return count
    except Exception as e:
        logger.error(f"Error counting orderdetails: {e}")
        return 0


def get_productlines_count(db: Session) -> int:
    logger.info("DB query: COUNT productlines")
    try:
        count = db.query(func.count(
            models.ProductLine.productLine)).scalar() or 0
        logger.info(f"productlines count = {count}")
        return count
    except Exception as e:
        logger.error(f"Error counting productlines: {e}")
        return 0
