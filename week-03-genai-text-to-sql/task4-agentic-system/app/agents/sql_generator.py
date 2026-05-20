from agents.llm import llm_client
from prompts import GENERATOR_SYSTEM_PROMPT


def generate_raw_sql(plan: str, previous_error: str = None) -> str:
    """Transforms a strategy plan into a valid PostgreSQL SELECT script."""
    user_payload = f"Strategy Plan: {plan}"
    if previous_error:
        user_payload += f"\n\nCRITICAL: Your previous generation failed with error: {previous_error}. Please correct the syntax."

    sql = llm_client.chat(GENERATOR_SYSTEM_PROMPT, user_payload)
    # Post-process to remove clean accidental markdown wrappers safely
    return sql.strip().strip(";").strip("`").replace("sql\n", "", 1)
