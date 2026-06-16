# Week 2 – Agentic Software Development: Database & API

## Overview
A progressive API project built on the ClassicModels PostgreSQL database following the Twelve-Factor App methodology. Each task adds a new layer from raw database setup to a full concurrent REST API with clean separation of concerns across all layers.

## Tasks

- **Task 1:** Set up a PostgreSQL database using Docker Compose with automatic seeding via `seed.sql`, demonstrating Factor III (Config), Factor IV (Backing Services), and Factor X (Dev/Prod Parity).
- **Task 2:** Built a 4-layer Customer CRUD API (database → schemas → crud → router) with full Create, Read, Update, Delete operations, pagination, related orders/payments endpoints, Pydantic validation and structured logging across all layers
- **Task 3:** Extended the API with 8 individual table count endpoints and one aggregated `/overall_counts` endpoint that queries all 8 tables simultaneously using `asyncio.gather()` demonstrating Factor VIII (Concurrency)
- **Task 4:** Expanded the architecture to cover every table in the database — Products, ProductLines, Offices, Employees, Orders, OrderDetails, and Payments — each with its own dedicated schema, CRUD, and router file, resulting in a complete REST API with 50+ endpoints

## Stack

Python · FastAPI · SQLAlchemy · PostgreSQL · Docker · Pydantic · asyncio

## Project Structure

```
week-02-agentic-software-development/
├── task1-database-setup/
├── task2-customer-api/
├── task3-concurrency-dashboard/
├── task4-full-rest-api/
```

## Run

Each task runs independently:

```bash
# Clone the repository first
git clone https://github.com/nikeshbhattarai1/fusemachines-ai-fellowship-2026
cd fusemachines-ai-fellowship-2026/week-02-agentic-software-development

# Task 1 — database only, no Python
cd task1-database-setup
cp .env.example .env        # fill in POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_PORT
docker compose up -d

# Task 2 — Customer CRUD API
cd task2-customer-api
cp .env.example .env
docker compose up -d
uvicorn app.main:app --reload
# visit http://localhost:8000/docs

# Task 3 — Concurrency dashboard
cd task3-concurrency-dashboard
cp .env.example .env
docker compose up -d
uvicorn app.main:app --reload
# visit http://localhost:8000/overall_counts

# Task 4 — Full REST API (all 8 tables)
cd task4-full-rest-api
cp .env.example .env
docker compose up -d
uvicorn main:app --reload
# visit http://localhost:8000/docs
```

## Twelve-Factor Principles Applied

| Factor | Description | Where |
|--------|-------------|-------|
| II — Dependencies | Exact library versions pinned | `requirements.txt` + virtual environment in Tasks 2, 3, 4 |
| III — Config | No hardcoded credentials anywhere | `.env` + `os.getenv()` across all tasks |
| IV — Backing Services | Database runs as a separate attached resource | Docker container in all tasks |
| VIII — Concurrency | All 8 DB queries run simultaneously | `asyncio.gather()` + `asyncio.to_thread()` in Task 3 |
| X — Dev/Prod Parity | Identical environment on every machine | `postgres:16` pinned image across all tasks |

---