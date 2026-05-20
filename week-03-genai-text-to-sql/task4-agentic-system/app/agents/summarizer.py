import json
from agents.llm import llm_client
from prompts import SUMMARIZER_SYSTEM_PROMPT


def summarize_results(user_query: str, db_results: list) -> str:
    """Formats database results into a natural language response."""
    user_payload = f"Original Query: {user_query}\n\nDatabase JSON Rows Raw Output:\n{json.dumps(db_results, indent=2)}"
    return llm_client.chat(SUMMARIZER_SYSTEM_PROMPT, user_payload, temperature=0.3)
