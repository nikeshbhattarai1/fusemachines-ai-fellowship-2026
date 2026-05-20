# Week 3 – GenAI: Text-to-SQL System


## Overview
A modular Text-to-SQL system that converts natural language questions into SQL queries, executes them on PostgreSQL and uses an agentic retry mechanism for reliability. Each task is self-contained with its own environment and Docker setup.

## Tasks
- **Task 1:** Wrote ground truth SQL queries for all benchmark questions and designed an evaluation framework for Text-to-SQL agents
- **Task 2:** Decomposed each natural language question into structured components: intent, tables, columns, filters and joins
- **Task 3:** Built a Text-to-SQL pipeline that generates SQL via LLM, executes it on PostgreSQL and auto-retries on failure
- **Task 4:** Wrapped the pipeline into a FastAPI agent with multi-step reasoning, self-correction (up to 3 retries) and natural language responses

## Stack
Python · FastAPI · PostgreSQL · SQLAlchemy · Groq (Llama 3.3)

## Run

Each task runs independently:

```bash
# Task 1 — see task1-sql-benchmark-preparation/Week_03_Task_1.pdf

# Task 2 — output saved in task2-text-to-sql/project/query_decomposition_results.docx
cd task2-text-to-sql/project
cp .env.template .env        # fill in your GROQ_API_KEY
python query_decomposition.py

# Task 3
cd task3-query-execution
cp .env.example .env         # fill in your GROQ_API_KEY
docker-compose up -d
python main.py

# Task 4
cd task4-agentic-system
cp .env.example .env         # fill in your GROQ_API_KEY
docker-compose up -d
uvicorn main:app --reload
```

## Benchmark Dataset
[SQL Questions](https://docs.google.com/spreadsheets/d/1lgh-Wk6wJMGSEZiQh_ILqVpuRn4UbPWFUnYzB1RZ9Qc)