from fastapi import FastAPI
from routers import (
    customer_router,
    product_router,
    productline_router,
    office_router,
    employee_router,
    order_router,
    orderdetail_router,
    payment_router,
)
from logger import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="ClassicModels Full REST API",
    description="Complete CRUD API for all ClassicModels tables.",
    version="4.0.0",
)

app.include_router(customer_router.router, prefix="/customers", tags=["Customers"])
app.include_router(product_router.router, prefix="/products", tags=["Products"])
app.include_router(productline_router.router, prefix="/productlines", tags=["ProductLines"])
app.include_router(office_router.router, prefix="/offices", tags=["Offices"])
app.include_router(employee_router.router, prefix="/employees", tags=["Employees"])
app.include_router(order_router.router, prefix="/orders", tags=["Orders"])
app.include_router(orderdetail_router.router, prefix="/orderdetails", tags=["OrderDetails"])
app.include_router(payment_router.router, prefix="/payments", tags=["Payments"])


@app.get("/", tags=["Root"])
def root():
    logger.info("Root endpoint accessed.")
    return {"message": "ClassicModels API is running! Visit /docs for the full API reference."}
