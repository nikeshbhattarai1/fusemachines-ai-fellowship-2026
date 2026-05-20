import streamlit as st
import pandas as pd
from graph.workflow import execute_agentic_pipeline

st.set_page_config(
    page_title="Agentic Text-to-SQL Assistant",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 Multi-Agent Text-to-SQL & Self-Correction Pipeline")
st.markdown(
    "This system processes complex natural language queries using independent planning, "
    "generation, verification, and self-correcting retry layers powered by **Llama 3.3 on Groq**."
)

if "messages" not in st.session_state:
    st.session_state.messages = []

# Show previous history logs
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "sql" in msg:
            st.code(msg["sql"], language="sql")
        if "df" in msg and msg["df"] is not None:
            st.dataframe(msg["df"])

# Handle user input
if user_input := st.chat_input("Ask a question (e.g., 'Show all customers from USA' or 'Count employees per job title')"):

    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("assistant"):
        with st.spinner("Orchestrating agent workflows and processing retries..."):
            final_state = execute_agentic_pipeline(user_input)

        # Display the final summary answer
        st.markdown(final_state.final_answer)

        # Display the generated SQL query
        if final_state.generated_sql:
            st.markdown("**Generated SQL Query:**")
            st.code(final_state.generated_sql, language="sql")

        # Display runtime errors, if any
        if final_state.errors:
            with st.expander("⚠️ Diagnostic Pipeline Trace Logs"):
                for err in final_state.errors:
                    st.caption(f"- {err}")

        # Render the result table
        df_display = None
        if final_state.execution_results:
            df_display = pd.DataFrame(final_state.execution_results)
            st.markdown(
                f"**Retrieved Database Rows ({len(df_display)} rows):**")
            st.dataframe(df_display, use_container_width=True)

        # Cache message history context
        st.session_state.messages.append({
            "role": "assistant",
            "content": final_state.final_answer,
            "sql": final_state.generated_sql,
            "df": df_display
        })
