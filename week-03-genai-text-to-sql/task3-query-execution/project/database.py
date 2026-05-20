import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres_secure_pass@localhost:5432/classicmodels")

def get_connection():
    """Establishes and returns a connection to the PostgreSQL database."""
    return psycopg2.connect(DATABASE_URL)

def execute_query_raw(sql_query: str):
    """
    Executes a raw SQL statement and returns a tuple: (list of dict rows, error message if any).
    Uses RealDictCursor so rows map columns natively to key-value maps.
    """
    conn = None
    try:
        conn = get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql_query)
            # DML safety sanity precaution check
            if cur.description:
                rows = [dict(row) for row in cur.fetchall()]
            else:
                rows = []
            conn.commit()
            return rows, None
    except Exception as e:
        if conn:
            conn.rollback()
        return None, str(e)
    finally:
        if conn:
            conn.close()