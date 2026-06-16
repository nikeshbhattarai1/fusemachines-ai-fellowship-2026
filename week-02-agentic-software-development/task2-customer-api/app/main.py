from fastapi import FastAPI
from app.router import router as customers_router
from app.logger import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="Classic Models API",
    description="A FastAPI service for managing customers with basic CRUD operations.",
    version="2.0.0",
)

app.include_router(customers_router, prefix="/customers")

logger.info("FastAPI app started. Docs → http://localhost:8000/docs")
