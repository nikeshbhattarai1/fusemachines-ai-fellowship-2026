import sys
from graph.workflow import execute_agentic_pipeline


def run_cli_pipeline():
    """Runs the pipeline directly via terminal command-line prompt ingestion."""
    if len(sys.argv) < 2:
        print("Usage: python main.py 'Your analytical query text string here'")
        sys.exit(1)

    query_string = sys.argv[1]
    print(f"\nProcessing Pipeline Request: '{query_string}'...\n")

    final_state = execute_agentic_pipeline(query_string)

    print("--- GENERATED SQL ---")
    print(final_state.generated_sql)
    print("\n--- EXECUTIVE SUMMARY ---")
    print(final_state.final_answer)


if __name__ == "__main__":
    run_cli_pipeline()
