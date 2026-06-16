from fastapi import FastAPI
from app.router import router
from app.logger import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="Classic Models API",
    description="Mastering Factor VIII: Concurrency",
    version="3.0.0",
)

app.include_router(router)

logger.info("App started → http://localhost:8000/docs")
