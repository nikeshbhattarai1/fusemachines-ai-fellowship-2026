from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from crud import office_crud
from schemas.office_schemas import OfficeCreate, OfficeUpdate, OfficeOut
from database import get_db
from logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Offices"])


@router.get("/", response_model=List[OfficeOut])
def list_offices(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    logger.info(f"GET /offices skip={skip} limit={limit}")
    offices = office_crud.get_offices(db, skip=skip, limit=limit)
    logger.info(f"GET /offices — returned {len(offices)} records.")
    return offices


@router.get("/{office_code}/employees", response_model=OfficeOut)
def get_office_with_employees(office_code: str, db: Session = Depends(get_db)):
    logger.info(f"GET /offices/{office_code}/employees")
    result = office_crud.get_office_with_employees(db, office_code)
    logger.info(
        f"GET /offices/{office_code}/employees — returned {len(result.employees)} employees.")
    return result


@router.get("/{office_code}", response_model=OfficeOut)
def get_office(office_code: str, db: Session = Depends(get_db)):
    logger.info(f"GET /offices/{office_code}")
    office = office_crud.get_office(db, office_code)
    if not office:
        logger.warning(f"GET /offices/{office_code} — 404 not found.")
        raise HTTPException(
            status_code=404, detail=f"Office '{office_code}' not found.")
    return office


@router.post("/", response_model=OfficeOut, status_code=201)
def create_office(data: OfficeCreate, db: Session = Depends(get_db)):
    logger.info(f"POST /offices officeCode={data.officeCode}")
    result = office_crud.create_office(db, data)
    logger.info(f"POST /offices — created officeCode={result.officeCode}")
    return result


@router.put("/{office_code}", response_model=OfficeOut)
def update_office(office_code: str, updates: OfficeUpdate, db: Session = Depends(get_db)):
    logger.info(f"PUT /offices/{office_code}")
    result = office_crud.update_office(db, office_code, updates)
    logger.info(f"PUT /offices/{office_code} — updated successfully.")
    return result


@router.delete("/{office_code}", status_code=204)
def delete_office(office_code: str, db: Session = Depends(get_db)):
    logger.info(f"DELETE /offices/{office_code}")
    office_crud.delete_office(db, office_code)
    logger.info(f"DELETE /offices/{office_code} — deleted successfully.")
