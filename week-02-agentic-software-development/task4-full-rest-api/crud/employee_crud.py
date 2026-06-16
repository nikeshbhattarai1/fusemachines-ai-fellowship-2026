from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
import models
from schemas.employee_schemas import EmployeeCreate, EmployeeUpdate
from logger import get_logger

logger = get_logger(__name__)


def get_employees(db: Session, skip: int = 0, limit: int = 100):
    logger.info(f"DB query: list employees | skip={skip} limit={limit}")
    employees = db.query(models.Employee).offset(skip).limit(limit).all()
    logger.info(f"Returned {len(employees)} employees.")
    return employees


def get_employee(db: Session, employee_number: int):
    logger.info(f"DB query: get employee employeeNumber={employee_number}")
    employee = (
        db.query(models.Employee)
        .filter(models.Employee.employeeNumber == employee_number)
        .first()
    )
    if employee is None:
        logger.warning(f"Employee not found: employeeNumber={employee_number}")
    else:
        logger.info(
            f"Found employee: {employee.firstName} {employee.lastName}")
    return employee


def create_employee(db: Session, data: EmployeeCreate):
    logger.info(
        f"DB query: create employee employeeNumber={data.employeeNumber}")
    existing = db.query(models.Employee).filter(
        models.Employee.employeeNumber == data.employeeNumber
    ).first()
    if existing:
        logger.warning(
            f"Employee already exists: employeeNumber={data.employeeNumber}")
        raise HTTPException(
            status_code=409,
            detail=f"Employee {data.employeeNumber} already exists."
        )
    db_employee = models.Employee(**data.model_dump())
    db.add(db_employee)
    try:
        db.commit()
        db.refresh(db_employee)
    except IntegrityError as e:
        db.rollback()
        logger.warning(f"FK constraint error creating employee: {e}")
        raise HTTPException(
            status_code=422,
            detail="Invalid officeCode or reportsTo value — referenced record does not exist."
        )
    logger.info(
        f"Employee created: employeeNumber={db_employee.employeeNumber}")
    return db_employee


def update_employee(db: Session, employee_number: int, updates: EmployeeUpdate):
    logger.info(f"DB query: update employee employeeNumber={employee_number}")
    db_employee = get_employee(db, employee_number)
    if db_employee is None:
        logger.warning(
            f"Update failed — employee {employee_number} not found.")
        raise HTTPException(
            status_code=404, detail=f"Employee {employee_number} not found.")
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_employee, field, value)
    try:
        db.commit()
        db.refresh(db_employee)
    except IntegrityError as e:
        db.rollback()
        logger.warning(f"FK constraint error updating employee: {e}")
        raise HTTPException(
            status_code=422, detail="Invalid foreign key value provided.")
    logger.info(f"Employee {employee_number} updated successfully.")
    return db_employee


def delete_employee(db: Session, employee_number: int):
    logger.info(f"DB query: delete employee employeeNumber={employee_number}")
    db_employee = get_employee(db, employee_number)
    if db_employee is None:
        logger.warning(
            f"Delete failed — employee {employee_number} not found.")
        raise HTTPException(
            status_code=404, detail=f"Employee {employee_number} not found.")
    db.delete(db_employee)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        logger.warning(
            f"FK constraint error deleting employee {employee_number}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete employee {employee_number} — they have direct reports or assigned customers."
        )
    logger.info(f"Employee {employee_number} deleted.")
    return True


def get_employee_with_customers(db: Session, employee_number: int):
    logger.info(
        f"DB query: get employee with customers employeeNumber={employee_number}")
    employee = get_employee(db, employee_number)
    if employee is None:
        raise HTTPException(
            status_code=404, detail=f"Employee {employee_number} not found.")
    customers = (
        db.query(models.Customer)
        .filter(models.Customer.salesRepEmployeeNumber == employee_number)
        .all()
    )
    logger.info(
        f"Found {len(customers)} customers for employee {employee_number}.")
    return employee, customers


def get_employee_reports(db: Session, employee_number: int):
    logger.info(f"DB query: get reports for employeeNumber={employee_number}")
    employee = get_employee(db, employee_number)
    if employee is None:
        raise HTTPException(
            status_code=404, detail=f"Employee {employee_number} not found.")
    reports = (
        db.query(models.Employee)
        .filter(models.Employee.reportsTo == employee_number)
        .all()
    )
    logger.info(
        f"Found {len(reports)} direct reports for employee {employee_number}.")
    return reports
