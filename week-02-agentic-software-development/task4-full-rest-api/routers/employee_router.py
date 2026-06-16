from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from crud import employee_crud
from schemas.employee_schemas import EmployeeCreate, EmployeeUpdate, EmployeeOut, EmployeeWithCustomersOut
from database import get_db
from logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Employees"])


@router.get("/", response_model=List[EmployeeOut])
def list_employees(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    logger.info(f"GET /employees skip={skip} limit={limit}")
    employees = employee_crud.get_employees(db, skip=skip, limit=limit)
    logger.info(f"GET /employees — returned {len(employees)} records.")
    return employees


@router.get("/{employee_number}/customers", response_model=EmployeeWithCustomersOut)
def get_employee_with_customers(employee_number: int, db: Session = Depends(get_db)):
    logger.info(f"GET /employees/{employee_number}/customers")
    employee, customers = employee_crud.get_employee_with_customers(
        db, employee_number)
    logger.info(
        f"GET /employees/{employee_number}/customers — returned {len(customers)} customers.")
    # Build response manually since customers is a separate query result
    result = EmployeeWithCustomersOut.model_validate(employee)
    result.customers = customers
    return result


@router.get("/{employee_number}/reports", response_model=List[EmployeeOut])
def get_employee_reports(employee_number: int, db: Session = Depends(get_db)):
    logger.info(f"GET /employees/{employee_number}/reports")
    reports = employee_crud.get_employee_reports(db, employee_number)
    logger.info(
        f"GET /employees/{employee_number}/reports — returned {len(reports)} direct reports.")
    return reports


@router.get("/{employee_number}", response_model=EmployeeOut)
def get_employee(employee_number: int, db: Session = Depends(get_db)):
    logger.info(f"GET /employees/{employee_number}")
    employee = employee_crud.get_employee(db, employee_number)
    if not employee:
        logger.warning(f"GET /employees/{employee_number} — 404 not found.")
        raise HTTPException(
            status_code=404, detail=f"Employee {employee_number} not found.")
    return employee


@router.post("/", response_model=EmployeeOut, status_code=201)
def create_employee(data: EmployeeCreate, db: Session = Depends(get_db)):
    logger.info(f"POST /employees employeeNumber={data.employeeNumber}")
    result = employee_crud.create_employee(db, data)
    logger.info(
        f"POST /employees — created employeeNumber={result.employeeNumber}")
    return result


@router.put("/{employee_number}", response_model=EmployeeOut)
def update_employee(employee_number: int, updates: EmployeeUpdate, db: Session = Depends(get_db)):
    logger.info(f"PUT /employees/{employee_number}")
    result = employee_crud.update_employee(db, employee_number, updates)
    logger.info(f"PUT /employees/{employee_number} — updated successfully.")
    return result


@router.delete("/{employee_number}", status_code=204)
def delete_employee(employee_number: int, db: Session = Depends(get_db)):
    logger.info(f"DELETE /employees/{employee_number}")
    employee_crud.delete_employee(db, employee_number)
    logger.info(f"DELETE /employees/{employee_number} — deleted successfully.")
