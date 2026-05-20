import re


def validate_sql_security(sql_query: str) -> tuple:
    """
    Strict rule-based security scanner to block Data Manipulation Language (DML) 
    and Data Definition Language (DDL) vectors. Ensures the system remains read-only.
    """
    clean_query = re.sub(r'--.*$', '', sql_query,
                         flags=re.MULTILINE)  # strip single-line comments
    clean_query = re.sub(r'/\*.*?\*/', '', clean_query,
                         flags=re.DOTALL)  # strip multi-line blocks

    # Tokenize alpha strings safely
    tokens = re.findall(r'\b[a-zA-Z]+\b', clean_query.upper())

    # SQL query block rules checking whitelist behavior
    if "SELECT" not in tokens:
        return False, "Security Exception: Statement must execute an explicit 'SELECT' command workflow."

    forbidden_keywords = {"DELETE", "DROP", "UPDATE", "INSERT",
                          "ALTER", "TRUNCATE", "GRANT", "REVOKE", "CREATE"}

    triggered_violations = forbidden_keywords.intersection(set(tokens))
    if triggered_violations:
        return False, f"Security Exception: Write-operation keyword violation detected: {list(triggered_violations)}"

    return True, None
