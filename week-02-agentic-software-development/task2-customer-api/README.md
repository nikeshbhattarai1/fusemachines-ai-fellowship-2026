# Task 2 — Classic Models Customer API

A FastAPI + PostgreSQL CRUD API for managing customers, orders and payments from the Classic Models database.
Implements full CRUD operations on the customers table with related orders and payments, following the Twelve-Factor App methodology.

---

## Features

* Customer CRUD (Create, Read, Update, Delete)
* Fetch customer orders and payments
* PostgreSQL database (Dockerized)
* SQLAlchemy ORM
* Pydantic validation (v2)
* Structured logging (console + file)
* Environment-based configuration (.env)

---

## Project Structure

```
task2-customer-api/
├── app/
│   ├── __init__.py       # Package initialization
│   ├── main.py           # FastAPI entry point 
│   ├── router.py         # API route definitions 
│   ├── crud.py           # Database query logic
│   ├── models.py         # SQLAlchemy ORM models
│   ├── database.py       # DB engine & session setup
│   ├── schemas.py        # Pydantic validation schemas
│   └── logger.py         # Logging configuration
│
├── logs/
│   └── .gitkeep          # Keeps logs directory in version control
│
├── sql/
│   └── seed.sql          # Database seed script (initial data setup)
│
├── .env.example          # Environment variable template
├── .gitignore
├── docker-compose.yml
├── requirements.txt
├── reflection.md
└── README.md
```

---

## Prerequisites

* Python 3.10+
* Docker and Docker Compose

---

## Setup Instructions

### 1. Clone the repository

```bash
https://github.com/nikeshbhattarai1/fusemachines-ai-fellowship-2026.git
cd fusemachines-ai-fellowship-2026/week-02-agentic-software-development/task2-customer-api
```

---

### 2. Copy the env template and fill in your values

```bash
cp .env.example .env
```

---

### 3. Start the database

```bash
docker compose up -d
```

---

### 4. Create a virtual environment and install dependencies

```bash
python -m venv venv
venv\Scripts\activate 
pip install -r requirements.txt
```

---

### 5. Run the API

```bash
uvicorn app.main:app --reload
```

Docs available at: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Endpoints

| Method | Endpoint                   | Description                               |
| ------ | -------------------------- | ----------------------------------------- |
| GET    | `/customers/`              | List all customers                        |
| GET    | `/customers/{id}`          | Get one customer with orders and payments |
| POST   | `/customers/`              | Create a customer                         |
| PUT    | `/customers/{id}`          | Partial update                            |
| DELETE | `/customers/{id}`          | Delete a customer                         |
| GET    | `/customers/{id}/orders`   | All orders for a customer                 |
| GET    | `/customers/{id}/payments` | All payments for a customer               |

---

## 6. Stopping the Database

```bash
docker compose down
```

To also wipe the data and start fresh:

```bash
docker compose down -v
```

---
