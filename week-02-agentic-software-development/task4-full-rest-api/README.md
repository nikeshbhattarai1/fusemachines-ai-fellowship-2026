# Task 4 — ClassicModels Full REST API

A complete FastAPI application providing full CRUD operations for all tables in the ClassicModels PostgreSQL database. This API extends a relational database into a fully functional REST service covering all 8 ClassicModels tables including relationships and composite key handling.

---

## Tech Stack

Python · FastAPI · SQLAlchemy · PostgreSQL · Pydantic · Docker

---

## Project Structure

```
task4-full-rest-api/
├── main.py                        # FastAPI entry point
├── database.py                    # DB engine and session (Connection Layer)
├── models.py                      # SQLAlchemy ORM models
├── logger.py                      # Centralized logging configuration
│
├── schemas/                      # Validation Layer (Pydantic)
│   ├── __init__.py
│   ├── customer_schemas.py
│   ├── product_schemas.py
│   ├── productline_schemas.py
│   ├── office_schemas.py
│   ├── employee_schemas.py
│   ├── order_schemas.py
│   ├── orderdetail_schemas.py
│   └── payment_schemas.py
│
├── crud/                         # Data Access Layer
│   ├── __init__.py
│   ├── customer_crud.py
│   ├── product_crud.py
│   ├── productline_crud.py
│   ├── office_crud.py
│   ├── employee_crud.py
│   ├── order_crud.py
│   ├── orderdetail_crud.py
│   └── payment_crud.py
│
├── routers/                      # API Layer
│   ├── __init__.py
│   ├── customer_router.py
│   ├── product_router.py
│   ├── productline_router.py
│   ├── office_router.py
│   ├── employee_router.py
│   ├── order_router.py
│   ├── orderdetail_router.py
│   └── payment_router.py
│
├── sql/
│   └── seed.sql                  # Schema + sample data
│
├── logs/
│   └── .gitkeep
│
├── .env.example
├── .gitignore
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## Architecture Overview

This project follows a strict 4-layer architecture:

| Layer            | Location      | Responsibility                         |
| ---------------- | ------------- | -------------------------------------- |
| Connection Layer | `database.py` | DB engine + session management         |
| Schema Layer     | `schemas/`    | Request/response validation (Pydantic) |
| CRUD Layer       | `crud/`       | Database operations per table          |
| Router Layer     | `routers/`    | HTTP endpoints and request handling    |

Each table follows this same structure for consistency and scalability.

---

## Prerequisites

* Python 3.10+
* Docker + Docker Compose

---

## Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/nikeshbhattarai1/fusemachines-ai-fellowship-2026.git
cd fusemachines-ai-fellowship-2026/week-02-agentic-software-development/task4-full-rest-api
```

---

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env`:

```env
POSTGRES_USER=your_username
POSTGRES_PASSWORD=your_password
POSTGRES_DB=classicmodels
POSTGRES_PORT=5432
```

> Ensure `.env` is never committed (already in `.gitignore`)

---

### 3. Start PostgreSQL database

```bash
docker compose up -d
```

On first run, `sql/seed.sql` automatically:

* creates all 8 tables
* inserts sample data

Check status:

```bash
docker compose ps
```

---

### 4. Create virtual environment

```bash
python -m venv venv

# Linux / macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

---

### 5. Install dependencies

```bash
pip install -r requirements.txt
```

---

### 6. Run the API

```bash
uvicorn main:app --reload
```

* API: [http://localhost:8000](http://localhost:8000)
* Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## API Endpoints

---

## Customers `/customers`

| Method | Endpoint                                | Description                         |
| ------ | --------------------------------------- | ----------------------------------- |
| GET    | `/customers/`                           | List all customers                  |
| GET    | `/customers/{customer_number}`          | Get customer with orders & payments |
| POST   | `/customers/`                           | Create new customer                 |
| PUT    | `/customers/{customer_number}`          | Partial update                      |
| DELETE | `/customers/{customer_number}`          | Delete customer                     |
| GET    | `/customers/{customer_number}/orders`   | Customer’s orders                   |
| GET    | `/customers/{customer_number}/payments` | Customer’s payments                 |

---

## Products `/products`

| Method | Endpoint                               | Description                            |
| ------ | -------------------------------------- | -------------------------------------- |
| GET    | `/products/`                           | List all products                      |
| GET    | `/products/{productCode}`              | Get product                            |
| GET    | `/products/{productCode}/orderdetails` | Product order history                  |
| POST   | `/products/`                           | Create product                         |
| PUT    | `/products/{productCode}`              | Update product                         |
| DELETE | `/products/{productCode}`              | Delete product (blocked if referenced) |

---

## ProductLines `/productlines`

| Method | Endpoint                               | Description                |
| ------ | -------------------------------------- | -------------------------- |
| GET    | `/productlines/`                       | List product lines         |
| GET    | `/productlines/{productLine}`          | Get product line           |
| GET    | `/productlines/{productLine}/products` | Products in line           |
| POST   | `/productlines/`                       | Create product line        |
| PUT    | `/productlines/{productLine}`          | Update product line        |
| DELETE | `/productlines/{productLine}`          | Delete (blocked if in use) |

---

## Offices `/offices`

| Method | Endpoint                          | Description      |
| ------ | --------------------------------- | ---------------- |
| GET    | `/offices/`                       | List offices     |
| GET    | `/offices/{officeCode}`           | Get office       |
| GET    | `/offices/{officeCode}/employees` | Office employees |
| POST   | `/offices/`                       | Create office    |
| PUT    | `/offices/{officeCode}`           | Update office    |
| DELETE | `/offices/{officeCode}`           | Delete office    |

---

## Employees `/employees`

| Method | Endpoint                                | Description       |
| ------ | --------------------------------------- | ----------------- |
| GET    | `/employees/`                           | List employees    |
| GET    | `/employees/{employeeNumber}`           | Get employee      |
| GET    | `/employees/{employeeNumber}/customers` | Managed customers |
| GET    | `/employees/{employeeNumber}/reports`   | Direct reports    |
| POST   | `/employees/`                           | Create employee   |
| PUT    | `/employees/{employeeNumber}`           | Update employee   |
| DELETE | `/employees/{employeeNumber}`           | Delete employee   |

---

## Orders `/orders`

| Method | Endpoint                             | Description        |
| ------ | ------------------------------------ | ------------------ |
| GET    | `/orders/`                           | List orders        |
| GET    | `/orders/{orderNumber}`              | Get order          |
| GET    | `/orders/{orderNumber}/orderdetails` | Order items        |
| GET    | `/orders/customer/{customerNumber}`  | Orders by customer |
| POST   | `/orders/`                           | Create order       |
| PUT    | `/orders/{orderNumber}`              | Update order       |
| DELETE | `/orders/{orderNumber}`              | Delete order       |

---

## OrderDetails `/orderdetails`

Composite Key: `(orderNumber, productCode)`

| Method | Endpoint                                    | Description     |
| ------ | ------------------------------------------- | --------------- |
| GET    | `/orderdetails/`                            | List all items  |
| GET    | `/orderdetails/{orderNumber}/{productCode}` | Get item        |
| GET    | `/orderdetails/order/{orderNumber}`         | Items in order  |
| GET    | `/orderdetails/product/{productCode}`       | Product history |
| POST   | `/orderdetails/`                            | Add item        |
| PUT    | `/orderdetails/{orderNumber}/{productCode}` | Update item     |
| DELETE | `/orderdetails/{orderNumber}/{productCode}` | Remove item     |

---

## Payments `/payments`

Composite Key: `(customerNumber, checkNumber)`

| Method | Endpoint                                   | Description       |
| ------ | ------------------------------------------ | ----------------- |
| GET    | `/payments/`                               | List payments     |
| GET    | `/payments/{customerNumber}/{checkNumber}` | Get payment       |
| GET    | `/payments/customer/{customerNumber}`      | Customer payments |
| POST   | `/payments/`                               | Create payment    |
| PUT    | `/payments/{customerNumber}/{checkNumber}` | Update payment    |
| DELETE | `/payments/{customerNumber}/{checkNumber}` | Delete payment    |

---

## 7. Logging

The application logs all activity across layers:

* Console logging: `INFO+`
* File logging: `logs/app.log` (`DEBUG+`)

---

## 8. Stop Database

```bash
docker compose down
```

To reset data:

```bash
docker compose down -v
```

---