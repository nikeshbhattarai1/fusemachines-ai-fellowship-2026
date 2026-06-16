from pydantic import BaseModel
from typing import Optional, List
from logger import get_logger

logger = get_logger(__name__)


class EmployeeSimpleOut(BaseModel):
    employeeNumber: int
    firstName: str
    lastName: str
    jobTitle: str
    email: str
    model_config = {"from_attributes": True}


class OfficeCreate(BaseModel):
    officeCode: str
    city: str
    phone: str
    addressLine1: str
    addressLine2: Optional[str] = None
    state: Optional[str] = None
    country: str
    postalCode: str
    territory: str


class OfficeOut(BaseModel):
    officeCode: str
    city: str
    phone: str
    addressLine1: str
    addressLine2: Optional[str] = None
    state: Optional[str] = None
    country: str
    postalCode: str
    territory: str
    employees: List[EmployeeSimpleOut] = []
    model_config = {"from_attributes": True}


class OfficeUpdate(BaseModel):
    city: Optional[str] = None
    phone: Optional[str] = None
    addressLine1: Optional[str] = None
    addressLine2: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postalCode: Optional[str] = None
    territory: Optional[str] = None
