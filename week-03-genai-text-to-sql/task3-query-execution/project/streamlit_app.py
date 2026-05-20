import streamlit as pd_st
import pandas as pd
from executor import run_text_to_sql_pipeline

pd_st.set_page_config(
    page_title="Text-to-SQL Pipeline Assistant",
    page_icon="💾",
    layout="wide"
)

pd_st.title("💾 Text-to-SQL Pipeline and Query Execution Dashboard")
pd_st.markdown(
    "This system handles semantic queries on the **ClassicModels PostgreSQL DB** using a sequential "
    "**Prompt Chaining workflow** powered by **Llama 3.3 70B via Groq**."
)

# Sidebar configurations
pd_st.sidebar.header("Pipeline Parameters Ledger")
pd_st.sidebar.info(
    "• **Model:** `llama-3.3-70b-versatile` \n"
    "• **Constraint:** Pure Vanilla Python Loops\n"
    "• **Security Guardrails:** Enabled (SELECT only)"
)

# Initialize Session Chat Memory
if "messages" not in pd_st.session_state:
    pd_st.session_state.messages = []

# Display prior historic messages
for msg in pd_st.session_state.messages:
    with pd_st.chat_message(msg["role"]):
        pd_st.markdown(msg["content"])
        if "sql" in msg:
            pd_st.code(msg["sql"], language="sql")
        if "dataframe" in msg and msg["dataframe"] is not None:
            pd_st.dataframe(msg["dataframe"])

# User Query Interaction Prompt Entry
if user_prompt := pd_st.chat_input("Ask a question about your database (e.g., 'Count total number of employees per office')"):
    
    # Render user chat line
    with pd_st.chat_message("user"):
        pd_st.markdown(user_prompt)
    pd_st.session_state.messages.append({"role": "user", "content": user_prompt})
    
    # Process Pipeline Chain
    with pd_st.chat_message("assistant"):
        with pd_st.spinner("Processing Prompt Chain Execution Layers..."):
            pipeline_result = run_text_to_sql_pipeline(user_prompt)
            
        status = pipeline_result["status"]
        generated_sql = pipeline_result["sql"]
        rows = pipeline_result["result"]
        retry_flag = pipeline_result["retry_needed"]
        errors = pipeline_result["error_messages"]
        
        # Format the analytical diagnostic metrics output
        response_text = f"### Pipeline Status: **{status.upper()}**\n"
        response_text += f"- **Self-Correction Layer Triggered:** `{retry_flag}`\n"
        
        if errors:
            response_text += "\n**Diagnostic Context/Alert Logs:**\n"
            for error in errors:
                response_text += f"- *`{error}`*\n"
                
        pd_st.markdown(response_text)
        
        df_display = None
        if generated_sql:
            pd_st.markdown("**Generated Execution SQL Script:**")
            pd_st.code(generated_sql, language="sql")
            
        if status == "success" and rows:
            df_display = pd.DataFrame(rows)
            pd_st.markdown(f"**Query Execution Output Matrix ({len(df_display)} items):**")
            pd_st.dataframe(df_display, use_container_width=True)
        elif status == "success":
            pd_st.info("Query successfully committed, but returned empty zero-row values.")
            
        # Append back into historic session records tracking
        history_entry = {
            "role": "assistant",
            "content": response_text,
            "sql": generated_sql,
            "dataframe": df_display
        }
        pd_st.session_state.messages.append(history_entry)