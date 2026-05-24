import streamlit as st

from data.csv_manager import list_user_files
from data.schema_inspector import get_table_schema
from pipeline.query_executor import execute_query
from pipeline.sql_generator import generate_sql
from pipeline.sql_validator import validate_sql
from pipeline.viz_recommender import build_figure


def _render_result(df, viz_type, viz_config, selected):
    if viz_type == "text" and len(df) == 1 and len(df.columns) == 1:
        val = df.iloc[0, 0]
        metric_label = viz_config.get("title") or df.columns[0]
        st.metric(label=metric_label, value=f"{val:,}" if isinstance(val, (int, float)) else str(val))
    elif viz_type in ("bar", "line", "pie", "scatter"):
        fig = build_figure(df, viz_type, viz_config)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.dataframe(df, use_container_width=True)
    else:
        st.dataframe(df, use_container_width=True)
    st.caption(
        f"Source: **{selected['filename']}** ({selected['row_count']:,} rows) · {len(df):,} result row(s)"
    )


def show_query_page(user_id: str) -> None:
    st.header("Ask Your Data")

    files = list_user_files(user_id)
    if not files:
        st.info("No datasets yet — upload a CSV in the **My Datasets** tab first.")
        return

    file_options = {f["filename"]: f for f in files}

    col1, col2 = st.columns([3, 1])
    with col1:
        selected_name = st.selectbox("Select a dataset", list(file_options.keys()))
    with col2:
        st.write("")
        st.write("")
        if st.button("Clear history", use_container_width=True):
            st.session_state[f"query_history_{file_options[selected_name]['table_name']}"] = []
            st.rerun()

    selected = file_options[selected_name]

    st.caption(
        f"{selected['row_count']:,} rows · "
        f"{len(selected['columns_info'])} columns: "
        f"{', '.join(c['name'] for c in selected['columns_info'][:6])}"
        + (" ..." if len(selected["columns_info"]) > 6 else "")
    )

    # Init conversation history per dataset
    history_key = f"query_history_{selected['table_name']}"
    if history_key not in st.session_state:
        st.session_state[history_key] = []
    history = st.session_state[history_key]

    # Render prior turns
    for turn in history:
        with st.chat_message("user"):
            st.write(turn["question"])
        with st.chat_message("assistant"):
            with st.expander("Generated SQL", expanded=False):
                st.code(turn["sql"], language="sql")
                if turn.get("explanation"):
                    st.caption(turn["explanation"])
            if turn.get("df") is not None:
                _render_result(turn["df"], turn["viz_type"], turn["viz_config"], selected)

    # Chat input
    question = st.chat_input(
        "Ask a question or follow up on the previous result…",
        key="sql_chat_input",
    )

    if not question:
        return

    with st.chat_message("user"):
        st.write(question)

    allowed_tables = {f["table_name"] for f in files}
    schema_str = get_table_schema(
        selected["table_name"], selected["columns_info"], selected["row_count"]
    )

    with st.chat_message("assistant"):
        with st.spinner("Generating SQL with AI..."):
            result = generate_sql(
                question,
                selected["table_name"],
                schema_str,
                chat_history=history,
            )

        if "error" in result:
            st.error(f"Couldn't answer that question: {result['error']}")
            st.info("Try rephrasing — e.g. be specific about column names or use simpler phrasing.")
            return

        sql = result.get("sql", "")
        explanation = result.get("explanation", "")
        viz_type = result.get("viz_type", "table")
        viz_config = result.get("viz_config", {})

        # Safety validation
        is_valid, val_error = validate_sql(sql, allowed_tables)
        if not is_valid:
            st.error(f"Generated query failed safety check: {val_error}")
            with st.expander("Blocked query"):
                st.code(sql, language="sql")
            return

        with st.expander("Generated SQL", expanded=False):
            st.code(sql, language="sql")
            if explanation:
                st.caption(explanation)

        with st.spinner("Running query..."):
            df, exec_error = execute_query(sql)

        if exec_error:
            st.error(f"Query execution failed: {exec_error}")
            st.info("The AI may have used an incorrect column name. Try rephrasing your question.")
            return

        if df is None or df.empty:
            st.warning("Query ran successfully but returned no results.")
            st.caption(f"Source: **{selected['filename']}** ({selected['row_count']:,} rows)")
            history.append({
                "question": question, "sql": sql, "explanation": explanation,
                "viz_type": viz_type, "viz_config": viz_config, "df": None,
            })
            return

        _render_result(df, viz_type, viz_config, selected)

        # Save turn to history
        history.append({
            "question": question,
            "sql": sql,
            "explanation": explanation,
            "viz_type": viz_type,
            "viz_config": viz_config,
            "df": df,
        })
