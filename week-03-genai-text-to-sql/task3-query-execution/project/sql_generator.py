import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from prompts.templates import DECOMPOSITION_PROMPT, GENERATION_PROMPT, FIXER_PROMPT

load_dotenv()

# Initialize vanilla wrapper around OpenAI SDK matching Groq specs
client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url=os.getenv("BASE_URL", "https://api.groq.com/openai/v1")
)

MODEL_NAME = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")


def call_llm(system_prompt: str, user_content: str, temperature: float = 0, max_tokens: int = 500) -> str:
    """Helper function to cleanly perform sequential atomic LLM completions."""
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        raise RuntimeError(f"LLM API Communication Error: {str(e)}")


def decompose_question(question: str) -> dict:
    """LLM Call 1: Extract JSON structure framework."""
    raw_response = call_llm(DECOMPOSITION_PROMPT,
                            f"User Question: \"{question}\"", max_tokens=300)

    # Simple resilient parser to strip occasional markdown json backticks if returned
    if raw_response.startswith("```"):
        raw_response = raw_response.strip("`").replace("json", "", 1).strip()

    try:
        return json.loads(raw_response)
    except Exception:
        # Fallback structural map if raw extraction was contaminated with conversational filler
        return {
            "Intent": "Decomposition Extraction Fallback",
            "Tables": [],
            "Columns": [],
            "Filters": "Raw structure fallback routing necessary.",
            "Joins": "None",
            "RawOutput": raw_response
        }


def generate_sql(decomposition: dict) -> str:
    """LLM Call 2: Generate executable PostgreSQL from JSON blueprints."""
    user_payload = f"Decomposed Criteria Structure JSON:\n{json.dumps(decomposition, indent=2)}"
    sql_text = call_llm(GENERATION_PROMPT, user_payload, max_tokens=400)
    return sql_text.strip().strip(";").strip("`").replace("sql\n", "", 1)


def self_correct_sql(original_sql: str, db_error_msg: str, question: str) -> str:
    """LLM Call 3: Fix syntax problems or missing joins using runtime error data."""
    user_payload = (
        f"Original Target Question: {question}\n"
        f"Attempted Failed SQL: {original_sql}\n"
        f"PostgreSQL Database Error Message: {db_error_msg}\n"
    )
    fixed_sql = call_llm(FIXER_PROMPT, user_payload, max_tokens=400)
    return fixed_sql.strip().strip(";").strip("`").replace("sql\n", "", 1)
