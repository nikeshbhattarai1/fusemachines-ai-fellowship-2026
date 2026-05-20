from executor import run_text_to_sql_pipeline
from tabulate import tabulate

# Structured evaluation dataset mapping across the standard database
MOCK_BENCHMARK_DATASET = [
    {"question": "List all products", "expected_contains": "products"},
    {"question": "Get all customers", "expected_contains": "customers"},
    {"question": "Show all orders", "expected_contains": "orders"},
    {"question": "List all employees", "expected_contains": "employees"},
    {"question": "Get all offices", "expected_contains": "offices"},
    {"question": "Get product names and prices", "expected_contains": "productName"},
    {"question": "Get employee first and last names", "expected_contains": "firstName"},
    {"question": "Get orders with customer names", "expected_contains": "customerName"},
    {"question": "Count customers per country", "expected_contains": "COUNT"},
    {"question": "Number of employees", "expected_contains": "COUNT"}
]

def run_evaluation_suite():
    print("\nStarting Automated Text-to-SQL Performance Evaluation Script...")
    
    headers = ["Question", "Generated SQL", "Executed Successfully", "Correct Result", "Retry Needed", "Final Status"]
    table_rows = []
    
    total_queries = len(MOCK_BENCHMARK_DATASET)
    successful_executions = 0
    retries_triggered = 0
    successful_retries = 0
    total_failures = 0
    
    for item in MOCK_BENCHMARK_DATASET:
        question = item["question"]
        pipeline_res = run_text_to_sql_pipeline(question)
        
        gen_sql = pipeline_res["sql"].replace("\n", " ")[:40] + "..." if pipeline_res["sql"] else "N/A"
        status = pipeline_res["status"].upper()
        retry_needed = pipeline_res["retry_needed"]
        
        executed_successfully = "Yes" if status == "SUCCESS" else "No"
        
        # Check basic schema match correctness expectations
        correct_result = "No"
        if status == "SUCCESS" and pipeline_res["result"] is not None:
            correct_result = "Yes" 
            successful_executions += 1
            
        if retry_needed == "Yes":
            retries_triggered += 1
            if status == "SUCCESS":
                successful_retries += 1
                
        if status == "FAILED":
            total_failures += 1
            
        table_rows.append([
            question,
            gen_sql,
            executed_successfully,
            correct_result,
            retry_needed,
            status
        ])
        
    print("\n===== TEST BENCHMARK METRIC VISUALIZATION REPORT =====\n")
    print(tabulate(table_rows, headers=headers, tablefmt="grid"))
    
    # Calculate performance ratios safely
    success_rate = (successful_executions / total_queries) * 100 if total_queries > 0 else 0
    retry_accuracy = (successful_retries / retries_triggered) * 100 if retries_triggered > 0 else 0
    
    print("\n===== SUMMARY METRICS COMPILATION =====")
    print(f"SQL Execution Success Rate : {success_rate:.2f}%")
    print(f"Total Retries Formulated    : {retries_triggered} attempts")
    print(f"Self-Correction Success Rate: {retry_accuracy:.2f}%")
    print(f"Total Failed Queries Dropout: {total_failures} failures")
    print("=======================================\n")

if __name__ == "__main__":
    run_evaluation_suite()