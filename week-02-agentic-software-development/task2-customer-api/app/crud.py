from sqlalchemy.orm import Session, joinedload
import app.models as models
import app.schemas as schemas
from app.logger import get_logger

logger = get_logger(__name__)


def get_customers(db: Session, skip: int = 0, limit: int = 100):
    logger.info(f"Fetching customers | skip={skip} limit={limit}")
    customers = db.query(models.Customer).offset(skip).limit(limit).all()
    logger.info(f"Returned {len(customers)} customers.")
    return customers


def get_customer(db: Session, customer_number: int):
    logger.info(f"Fetching customer with customerNumber={customer_number}")
    customer = (
        db.query(models.Customer)
        .options(joinedload(models.Customer.orders), joinedload(models.Customer.payments))
        .filter(models.Customer.customerNumber == customer_number)
        .first()
    )
    if customer is None:
        logger.warning(f"Customer not found: ID {customer_number}")
    else:
        logger.info(f"Found customer: {customer.customerName}")
    return customer


def create_customer(db: Session, customer: schemas.CustomerCreate):
    logger.info(f"Creating new customer: {customer.customerName}")
    max_num = db.query(models.Customer.customerNumber).order_by(
        models.Customer.customerNumber.desc()
    ).first()
    next_number = (max_num[0] + 1) if max_num else 1

    db_customer = models.Customer(
        customerNumber=next_number,
        customerName=customer.customerName,
        contactLastName=customer.contactLastName,
        contactFirstName=customer.contactFirstName,
        phone=customer.phone,
        addressLine1=customer.addressLine1,
        addressLine2=customer.addressLine2,
        city=customer.city,
        state=customer.state,
        postalCode=customer.postalCode,
        country=customer.country,
        salesRepEmployeeNumber=customer.salesRepEmployeeNumber,
        creditLimit=customer.creditLimit,
    )
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    db_customer = get_customer(db, db_customer.customerNumber)
    logger.info(
        f"Customer created with customerNumber={db_customer.customerNumber}")
    return db_customer


def update_customer(db: Session, customer_number: int, updates: schemas.CustomerUpdate):
    logger.info(f"Updating customer customerNumber={customer_number}")
    db_customer = get_customer(db, customer_number)
    if db_customer is None:
        logger.warning(
            f"Update failed — customer {customer_number} not found.")
        return None
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_customer, field, value)
    db.commit()
    db.refresh(db_customer)
    logger.info(f"Customer {customer_number} updated successfully.")
    return db_customer


def delete_customer(db: Session, customer_number: int):
    logger.info(f"Deleting customer customerNumber={customer_number}")
    db_customer = get_customer(db, customer_number)
    if db_customer is None:
        logger.warning(
            f"Delete failed — customer {customer_number} not found.")
        return False
    db.delete(db_customer)
    db.commit()
    logger.info(f"Customer {customer_number} deleted.")
    return True


def get_customer_orders(db: Session, customer_number: int):
    logger.info(f"Fetching orders for customerNumber={customer_number}")
    orders = (
        db.query(models.Order)
        .filter(models.Order.customerNumber == customer_number)
        .all()
    )
    logger.info(f"Found {len(orders)} orders for customer {customer_number}.")
    return orders


def get_customer_payments(db: Session, customer_number: int):
    logger.info(f"Fetching payments for customerNumber={customer_number}")
    payments = (
        db.query(models.Payment)
        .filter(models.Payment.customerNumber == customer_number)
        .all()
    )
    logger.info(
        f"Found {len(payments)} payments for customer {customer_number}.")
    return payments
