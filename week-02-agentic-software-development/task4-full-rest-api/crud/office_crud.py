from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
import models
from schemas.office_schemas import OfficeCreate, OfficeUpdate
from logger import get_logger

logger = get_logger(__name__)


def get_offices(db: Session, skip: int = 0, limit: int = 100):
    logger.info(f"DB query: list offices | skip={skip} limit={limit}")
    offices = db.query(models.Office).offset(skip).limit(limit).all()
    logger.info(f"Returned {len(offices)} offices.")
    return offices


def get_office(db: Session, office_code: str):
    logger.info(f"DB query: get office officeCode={office_code}")
    office = (
        db.query(models.Office)
        .options(joinedload(models.Office.employees))
        .filter(models.Office.officeCode == office_code)
        .first()
    )
    if office is None:
        logger.warning(f"Office not found: officeCode={office_code}")
    else:
        logger.info(f"Found office: {office.city}, {office.country}")
    return office


def create_office(db: Session, data: OfficeCreate):
    logger.info(f"DB query: create office officeCode={data.officeCode}")
    existing = db.query(models.Office).filter(
        models.Office.officeCode == data.officeCode
    ).first()
    if existing:
        logger.warning(f"Office already exists: officeCode={data.officeCode}")
        raise HTTPException(
            status_code=409, detail=f"Office '{data.officeCode}' already exists.")

    db_office = models.Office(**data.model_dump())
    db.add(db_office)
    db.commit()
    db.refresh(db_office)
    logger.info(f"Office created: officeCode={db_office.officeCode}")
    return get_office(db, db_office.officeCode)


def update_office(db: Session, office_code: str, updates: OfficeUpdate):
    logger.info(f"DB query: update office officeCode={office_code}")
    db_office = get_office(db, office_code)
    if db_office is None:
        logger.warning(f"Update failed — office {office_code} not found.")
        raise HTTPException(
            status_code=404, detail=f"Office '{office_code}' not found.")
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_office, field, value)
    db.commit()
    db.refresh(db_office)
    logger.info(f"Office {office_code} updated successfully.")
    return get_office(db, office_code)


def delete_office(db: Session, office_code: str):
    logger.info(f"DB query: delete office officeCode={office_code}")
    db_office = get_office(db, office_code)
    if db_office is None:
        logger.warning(f"Delete failed — office {office_code} not found.")
        raise HTTPException(
            status_code=404, detail=f"Office '{office_code}' not found.")
    db.delete(db_office)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        logger.warning(
            f"FK constraint error deleting office {office_code}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete office '{office_code}' — employees are still assigned to it."
        )
    logger.info(f"Office {office_code} deleted.")
    return True


def get_office_with_employees(db: Session, office_code: str):
    logger.info(
        f"DB query: get office with employees officeCode={office_code}")
    office = get_office(db, office_code)
    if office is None:
        raise HTTPException(
            status_code=404, detail=f"Office '{office_code}' not found.")
    logger.info(
        f"Found {len(office.employees)} employees for office {office_code}.")
    return office
