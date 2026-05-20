from sqlalchemy import text
from db import engine


def execute_sql_query(sql_string: str) -> list:
    """Executes validated SQL and returns a clean list of dictionaries."""
    with engine.connect() as connection:
        result = connection.execute(text(sql_string))
        # If the query returns rows (e.g., SELECT)
        if result.returns_rows:
            return [dict(row._mapping) for row in result]
        return [{"row_count_affected": result.rowcount}]
