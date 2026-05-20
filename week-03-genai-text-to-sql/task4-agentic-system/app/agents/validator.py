import re


def validate_sql_read_only(sql_string: str) -> tuple[bool, str | None]:
    """Ensures queries only contain SELECT statements and guards against destructive operations."""
    clean_sql = re.sub(r'--.*$', '', sql_string, flags=re.MULTILINE)
    clean_sql = re.sub(r'/\*.*?\*/', '', clean_sql, flags=re.DOTALL)

    tokens = re.findall(r'\b[a-zA-Z]+\b', clean_sql.upper())

    if "SELECT" not in tokens:
        return False, "Query verification exception: Query must execute an explicit 'SELECT' function."

    destructive_keywords = {"DROP", "DELETE", "UPDATE",
                            "INSERT", "TRUNCATE", "ALTER", "GRANT"}
    violations = destructive_keywords.intersection(set(tokens))

    if violations:
        return False, f"Guardrail Exception: Destructive DDL/DML operator identified: {list(violations)}"

    return True, None
