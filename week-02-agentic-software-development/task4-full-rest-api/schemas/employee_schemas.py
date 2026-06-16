from pydantic import BaseModel, EmailStr
from typing import Optional, List
from decimal import Decimal
from logger import get_logger

logger = get_logger(__name__)


class CustomerSimpleOut(BaseModel):
    customerNumber: int
    customerName: str
    city: str
    country: str
    creditLimit: Optional[Decimal] = None
    model_config = {"from_attributes": True}


class EmployeeCreate(BaseModel):
    employeeNumber: int
    lastName: str
    firstName: str
    extension: str
    email: EmailStr
    officeCode: str
    reportsTo: Optional[int] = None
    jobTitle: str


class EmployeeOut(BaseModel):
    employeeNumber: int
    lastName: str
    firstName: str
    extension: str
    email: str
    officeCode: str
    reportsTo: Optional[int] = None
    jobTitle: str
    model_config = {"from_attributes": True}


class EmployeeWithCustomersOut(BaseModel):
    employeeNumber: int
    lastName: str
    firstName: str
    extension: str
    email: str
    officeCode: str
    reportsTo: Optional[int] = None
    jobTitle: str
    customers: List[CustomerSimpleOut] = []
    model_config = {"from_attributes": True}


class EmployeeUpdate(BaseModel):
    lastName: Optional[str] = None
    firstName: Optional[str] = None
    extension: Optional[str] = None
    email: Optional[EmailStr] = None
    officeCode: Optional[str] = None
    reportsTo: Optional[int] = None
    jobTitle: Optional[str] = None
