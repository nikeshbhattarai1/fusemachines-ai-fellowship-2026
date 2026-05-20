from pydantic import BaseModel, Field
from agents.llm import llm_client
from agents.planner import generate_db_plan
from agents.sql_generator import generate_raw_sql
from agents.validator import validate_sql_read_only
from agents.executor import execute_agent_query
from agents.summarizer import summarize_results


class AgentWorkflowState(BaseModel):
    """Tracks state throughout the Text-to-SQL execution workflow."""
    user_query: str
    plan: str = ""
    generated_sql: str = ""
    is_valid_sql: bool = False
    execution_results: list = Field(default_factory=list)
    final_answer: str = ""
    errors: list[str] = Field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 2


def is_database_query(query: str) -> bool:
    """Guardrail to verify if the query explicitly targets the retail database data context."""
    system_prompt = (
        "You are a routing guardrail. Determine if the user's question can be answered "
        "by querying a retail database containing tables like customers, orders, products, orderdetails, payments, and employees. "
        "If the query is a general concept question (e.g., 'what is an LLM?'), general chat, or completely unrelated to pulling specific data "
        "records from this catalog schema, return NO. "
        "Return ONLY the exact string 'YES' or 'NO'. Do not provide any markdown, headers, or conversational prose."
    )
    try:
        response = llm_client.chat(system_prompt, f"User Query: {query}")
        return "YES" in response.upper()
    except Exception:
        return True


def execute_agentic_pipeline(query: str) -> AgentWorkflowState:
    """
    Orchestrates the Text-to-SQL pipeline using a state-based workflow.
    Handles planning, generation, validation, execution, and self-correction retries.
    """
    state = AgentWorkflowState(user_query=query)

    # Catch out-of-bounds questions before they hit the planning layer
    if not is_database_query(state.user_query):
        state.final_answer = (
            "I am a structured database assistant, and I can only help you with queries "
            "regarding our product catalog, customer records, orders, payments, or employees. "
            "Please ask a question related to our business database tables."
        )
        return state

    # Step 1: Planning
    state.plan = generate_db_plan(state.user_query)

    # Execution & Validation Loop
    while state.retry_count <= state.max_retries:
        # Step 2: Generation
        last_error = state.errors[-1] if state.errors else None
        state.generated_sql = generate_raw_sql(
            state.plan, previous_error=last_error)

        # Step 3: Security Validation
        is_safe, validation_error = validate_sql_read_only(state.generated_sql)
        if not is_safe:
            state.errors.append(f"Validation Failure: {validation_error}")
            state.retry_count += 1
            continue

        state.is_valid_sql = True

        # Step 4: Execution
        rows, db_error = execute_agent_query(state.generated_sql)
        if db_error:
            state.errors.append(f"PostgreSQL Engine Error: {db_error}")
            state.is_valid_sql = False
            state.retry_count += 1
            continue

        # Success checkpoint breakout
        state.execution_results = rows
        break

    # Step 5: Summarization / Final Output
    if state.execution_results or (state.is_valid_sql and state.errors == []):
        state.final_answer = summarize_results(
            state.user_query, state.execution_results)
    else:
        state.final_answer = (
            f"I encountered persistent issues processing your request. "
            f"Diagnostic Logs: {'; '.join(state.errors)}"
        )

    return state
