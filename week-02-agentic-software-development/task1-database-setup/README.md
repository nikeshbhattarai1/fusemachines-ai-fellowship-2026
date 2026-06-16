# Task 1 — PostgreSQL Database with Docker

Sets up a PostgreSQL database using Docker Compose demonstrating
Factor III (Config), Factor IV (Backing Services) and Factor X (Dev/Prod Parity)
from the Twelve-Factor App methodology.

---

## Project Structure

```
task1-database-setup/
├── seed.sql            # Creates all 8 tables and inserts sample data
├── docker-compose.yml  # Spins up PostgreSQL container
├── .env.example        # Environment variable template (copy to .env)
├── .gitignore
└── README.md
```

---

## Prerequisites

- Docker and Docker Compose installed

---

## Setup Instructions

### 1. Clone the repository

```bash
https://github.com/nikeshbhattarai1/fusemachines-ai-fellowship-2026.git
cd fusemachines-ai-fellowship-2026/week-02-agentic-software-development/task1-database-setup
```
---

### 2. Copy the env template and fill in your values

```bash
cp .env.example .env
```

Open `.env` and set your own username, password, database name and port.

Example:

```env
POSTGRES_USER=admin
POSTGRES_PASSWORD=admin123
POSTGRES_DB=classicmodels
POSTGRES_PORT=5432
```

---

### 3. Start the database

```bash
docker compose up -d
```

PostgreSQL starts and automatically runs `sql/seed.sql` creating all 8 tables
and loading sample data. No manual steps needed.

---

### ⚠️ Important note

If you change `.env` after the first run, reset the database:

```bash
docker compose down -v
docker compose up -d
```

---

### 4. Verify it is running

```bash
docker compose ps
```

The `db` container should show status `healthy`.

---

### 5. Connect and inspect

Enter the container:

```bash
docker exec -it classicmodels_db /bin/bash
```

Connect to PostgreSQL (use the values from your `.env`):

```bash
psql -U  -d 
```

List all tables:

```sql
\dt
```

You should see 8 tables: customers, orders, products, employees,
offices, payments, orderdetails, productlines.

Count rows in a table:

```sql
SELECT COUNT(*) FROM customers;
```
---

### 6. Stop the database

```bash
docker compose down
```

To also wipe the data and start fresh:

```bash
docker compose down -v
```

---

