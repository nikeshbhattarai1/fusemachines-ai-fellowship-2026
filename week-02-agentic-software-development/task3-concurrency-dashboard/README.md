# Task 3 — Classic Models API (Factor VIII: Concurrency)

A FastAPI-based backend built on the Classic Models database demonstrating Factor VIII (Concurrency) of the Twelve-Factor App.
The project executes multiple database aggregation queries in parallel using `asyncio.gather()` and `asyncio.to_thread()`, ensuring efficient concurrent performance.

---

## Features

* FastAPI REST API with SQLAlchemy ORM
* PostgreSQL database via Docker
* Clean layered architecture (models, CRUD, routing)
* Structured logging (console + file)
* Environment-based configuration using `.env`
* Concurrent database aggregation using `asyncio.gather()`
* Optimized `/overall_counts` endpoint for parallel execution

---

## Project Structure

```bash
task3-concurrency-dashboard/
├── app/
│   ├── __init__.py       # Package initialization
│   ├── main.py           # FastAPI entry point
│   ├── router.py         # API route definitions
│   ├── crud.py           # Database query logic
│   ├── models.py         # SQLAlchemy ORM models
│   ├── database.py       # DB engine & session setup
│   └── logger.py         # Logging configuration
│
├── sql/
│   └── seed.sql          # Database seed script
│
├── logs/
│   └── .gitkeep
│
├── .env.example          # Environment template
├── .gitignore
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## Prerequisites

* Python 3.10+
* Docker + Docker Compose

---

## Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/nikeshbhattarai1/fusemachines-ai-fellowship-2026
cd task3-concurrency-dashboard/week-02-agentic-software-development/task3-concurrency-dashboard
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

> Ensure `.env` is not committed (already included in `.gitignore`)

---

### 3. Start PostgreSQL database

```bash
docker compose up -d
```

Wait 10–15 seconds for the container to become healthy:

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
uvicorn app.main:app --reload
```

* API: [http://localhost:8000](http://localhost:8000)
* Swagger Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## API Endpoints

| Method | Endpoint              | Description                      |
| ------ | --------------------- | -------------------------------- |
| GET    | `/customers/count`    | Count rows in customers table    |
| GET    | `/orders/count`       | Count rows in orders table       |
| GET    | `/products/count`     | Count rows in products table     |
| GET    | `/employees/count`    | Count rows in employees table    |
| GET    | `/offices/count`      | Count rows in offices table      |
| GET    | `/payments/count`     | Count rows in payments table     |
| GET    | `/orderdetails/count` | Count rows in orderdetails table |
| GET    | `/productlines/count` | Count rows in productlines table |
| GET    | `/overall_counts`     | All counts fetched concurrently  |

---

## Concurrency Design

The `/overall_counts` endpoint demonstrates concurrency using:

* `asyncio.to_thread()` → runs blocking DB queries in separate threads
* `asyncio.gather()` → executes all queries in parallel

### Key idea:

Instead of executing queries sequentially:

```
T_total = T1 + T2 + ... + T8
```

They run concurrently:

```
T_total ≈ max(T1, T2, ... T8)
```

This significantly improves response time for aggregated workloads.

---

## Stopping the Database

```bash
docker compose down
```

To reset all data:

```bash
docker compose down -v
```

---

## Summary

This project demonstrates how concurrency in FastAPI can be used to optimize database-heavy operations while maintaining clean architecture and production-ready structure.

---

