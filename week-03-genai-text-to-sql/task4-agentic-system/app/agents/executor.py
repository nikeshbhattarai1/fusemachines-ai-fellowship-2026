from tools.db_tools import execute_sql_query


def execute_agent_query(sql_string: str) -> tuple[list | None, str | None]:
    """Wraps database engine processing to cleanly capture runtime error logs."""
    try:
        rows = execute_sql_query(sql_string)
        return rows, None
    except Exception as e:
        return None, str(e)
