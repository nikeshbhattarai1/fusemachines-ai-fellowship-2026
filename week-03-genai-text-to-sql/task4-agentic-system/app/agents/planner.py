from agents.llm import llm_client
from prompts import PLANNER_SYSTEM_PROMPT


def generate_db_plan(user_query: str) -> str:
    """Creates an execution strategy indicating required parameters."""
    return llm_client.chat(PLANNER_SYSTEM_PROMPT, f"User Query: {user_query}")
