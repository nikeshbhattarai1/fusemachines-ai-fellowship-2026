from pydantic import BaseModel
from typing import Optional, List
from logger import get_logger

logger = get_logger(__name__)


class ProductSimpleOut(BaseModel):
    productCode: str
    productName: str
    productScale: str
    productVendor: str
    quantityInStock: int
    model_config = {"from_attributes": True}


class ProductLineCreate(BaseModel):
    productLine: str
    textDescription: Optional[str] = None
    htmlDescription: Optional[str] = None
    # image excluded from create/update — binary data handled separately


class ProductLineOut(BaseModel):
    productLine: str
    textDescription: Optional[str] = None
    htmlDescription: Optional[str] = None
    # image intentionally excluded from JSON output (binary data)
    products: List[ProductSimpleOut] = []
    model_config = {"from_attributes": True}


class ProductLineUpdate(BaseModel):
    textDescription: Optional[str] = None
    htmlDescription: Optional[str] = None
