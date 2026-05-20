import os
import json
from datetime import datetime
from database import execute_query_raw
from sql_generator import decompose_question, generate_sql, self_correct_sql
from validator import validate_sql_security

LOG_FILE_PATH = os.path.join(os.path.dirname(__file__), "logs", "query_logs.json")

def append_execution_log(log_entry: dict):
    """Appends workflow metrics securely to a file-based ledger."""
    os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)
    
    logs = []
    if os.path.exists(LOG_FILE_PATH):
        try:
            with open(LOG_FILE_PATH, "r") as f:
                logs = json.load(f)
        except Exception:
            logs = []
            
    logs.append(log_entry)
    
    try:
        with open(LOG_FILE_PATH, "w") as f:
            json.dump(logs, f, indent=2)
    except Exception as e:
        print(f"Logging IO Error encountered: {e}")

def run_text_to_sql_pipeline(question: str) -> dict:
    """
    Main orchestration router mapping the exact prompt-chain sequence.
    Returns standard diagnostic dictionary profiles.
    """
    timestamp = datetime.utcnow().isoformat()
    output_template = {
        "timestamp": timestamp,
        "question": question,
        "decomposed_json": None,
        "sql": "",
        "result": [],
        "retry_needed": "No",
        "error_messages": [],
        "status": "failed"
    }
    
    try:
        # Step 1: Decomposition
        decomp = decompose_question(question)
        output_template["decomposed_json"] = decomp
        
        # Step 2: Generation
        generated_sql = generate_sql(decomp)
        output_template["sql"] = generated_sql
        
        # Step 3: Security Validation Check
        is_safe, sec_err = validate_sql_security(generated_sql)
        if not is_safe:
            output_template["error_messages"].append(sec_err)
            append_execution_log(output_template)
            return output_template
            
        # Step 4: Execution Attempt 1
        rows, db_err = execute_query_raw(generated_sql)
        
        if db_err is None:
            output_template["result"] = rows
            output_template["status"] = "success"
            append_execution_log(output_template)
            return output_template
            
        # Step 5: Self-Correction Entry Point (Strictly 1 Retry)
        output_template["retry_needed"] = "Yes"
        output_template["error_messages"].append(f"Attempt 1 DB Error: {db_err}")
        
        fixed_sql = self_correct_sql(generated_sql, db_err, question)
        output_template["sql"] = fixed_sql # Update tracked SQL reference
        
        # Re-Validate corrected SQL string
        is_safe_fixed, sec_err_fixed = validate_sql_security(fixed_sql)
        if not is_safe_fixed:
            output_template["error_messages"].append(f"Retry Safety Failure: {sec_err_fixed}")
            append_execution_log(output_template)
            return output_template
            
        # Attempt 2 execution
        rows_fixed, db_err_fixed = execute_query_raw(fixed_sql)
        if db_err_fixed is None:
            output_template["result"] = rows_fixed
            output_template["status"] = "success"
        else:
            output_template["error_messages"].append(f"Attempt 2 DB Error: {db_err_fixed}")
            output_template["status"] = "failed"
            
    except Exception as general_exc:
        output_template["error_messages"].append(f"Pipeline Runtime Exception: {str(general_exc)}")
        output_template["status"] = "failed"
        
    append_execution_log(output_template)
    return output_template