import streamlit as st

from data.csv_manager import list_user_files
from data.schema_inspector import get_table_schema
from pipeline.intent_detector import detect_intent
from pipeline.sql_generator import generate_sql
from pipeline.sql_validator import validate_sql
from pipeline.query_executor import execute_query
from pipeline.viz_recommender import build_figure
from rag.rag_pipeline import answer_question
from ui.rag_page import _list_pdfs

_SOURCE_LABELS = {
    "csv": ("Querying CSV data", "🗃️"),
    "pdf": ("Querying documents", "📄"),
    "both": ("Querying CSV + documents", "🔍"),
}


def _run_csv(question: str, user_id: str, csv_files: list[dict], suggested_filename: str = None) -> None:
    """Run NL-to-SQL on the best matching CSV."""
    allowed_tables = {f["table_name"] for f in csv_files}

    # Use LLM-suggested filename first, then heuristic, then first file
    if suggested_filename:
        selected = next((f for f in csv_files if f["filename"] == suggested_filename), None)
        if not selected:
            selected = _pick_csv(csv_files, question)
    elif len(csv_files) == 1:
        selected = csv_files[0]
    else:
        selected = _pick_csv(csv_files, question)

    schema_str = get_table_schema(
        selected["table_name"], selected["columns_info"], selected["row_count"]
    )

    with st.spinner("Generating SQL..."):
        result = generate_sql(question, selected["table_name"], schema_str)

    if "error" in result:
        st.error(f"Could not answer from CSV: {result['error']}")
        return

    sql = result.get("sql", "")
    explanation = result.get("explanation", "")
    viz_type = result.get("viz_type", "table")
    viz_config = result.get("viz_config", {})

    is_valid, val_error = validate_sql(sql, allowed_tables)
    if not is_valid:
        st.error(f"SQL safety check failed: {val_error}")
        return

    with st.expander("Generated SQL", expanded=False):
        st.code(sql, language="sql")
        if explanation:
            st.caption(explanation)

    with st.spinner("Running query..."):
        df, exec_error = execute_query(sql)

    if exec_error:
        st.error(f"Query failed: {exec_error}")
        return

    if df is None or df.empty:
        st.warning("Query returned no results.")
        return

    if viz_type == "text" and len(df) == 1 and len(df.columns) == 1:
        val = df.iloc[0, 0]
        label = viz_config.get("title") or df.columns[0]
        st.metric(label=label, value=f"{val:,}" if isinstance(val, (int, float)) else str(val))
    elif viz_type in ("bar", "line", "pie", "scatter"):
        fig = build_figure(df, viz_type, viz_config)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.dataframe(df, use_container_width=True)
    else:
        st.dataframe(df, use_container_width=True)

    st.caption(f"Source: **{selected['filename']}** ({selected['row_count']:,} rows) · {len(df):,} result row(s)")


def _pick_csv(csv_files: list[dict], question: str) -> dict:
    """When multiple CSVs exist, pick the one whose columns best match the question."""
    question_lower = question.lower()
    best, best_score = csv_files[0], 0
    for f in csv_files:
        score = sum(1 for c in f["columns_info"] if c["name"] in question_lower)
        if score > best_score:
            best, best_score = f, score
    return best


def _run_pdf(question: str, user_id: str) -> None:
    with st.spinner("Searching documents..."):
        result = answer_question(user_id, question)
    if "error" in result:
        st.error(result["error"])
        return
    st.write(result["answer"])
    if result["sources"]:
        source_strs = [f"**{s['filename']}**, p.{s['page']}" for s in result["sources"]]
        st.caption("Sources: " + " · ".join(source_strs))


def show_ask_page(user_id: str) -> None:
    st.header("Ask Anything")
    st.caption("Ask a question — the system automatically routes it to your CSV data, documents, or both.")

    csv_files = list_user_files(user_id)
    pdf_files = _list_pdfs(user_id)

    # Source availability summary
    col1, col2 = st.columns(2)
    with col1:
        if csv_files:
            st.success(f"🗃️ {len(csv_files)} CSV dataset(s) available")
        else:
            st.warning("No CSV datasets — upload one in **My Datasets**")
    with col2:
        if pdf_files:
            st.success(f"📄 {len(pdf_files)} PDF document(s) available")
        else:
            st.warning("No PDFs — upload one in **Document Q&A**")

    if not csv_files and not pdf_files:
        st.info("Upload a CSV or PDF first to start asking questions.")
        return

    st.divider()

    # Conversation history
    if "ask_history" not in st.session_state:
        st.session_state["ask_history"] = []

    for turn in st.session_state["ask_history"]:
        with st.chat_message("user"):
            st.write(turn["question"])
        with st.chat_message("assistant"):
            label, icon = _SOURCE_LABELS.get(turn["source"], ("", ""))
            st.caption(f"{icon} {label}")
            st.write(turn["answer_summary"])

    question = st.chat_input("Ask anything about your data or documents...")
    if not question:
        return

    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        # Determine routing
        if csv_files and not pdf_files:
            source = "csv"
            reasoning = "Only CSV data available."
        elif pdf_files and not csv_files:
            source = "pdf"
            reasoning = "Only PDF documents available."
        else:
            with st.spinner("Detecting best data source..."):
                intent = detect_intent(question, csv_files, pdf_files)
            source = intent["source"]
            reasoning = intent["reasoning"]

        label, icon = _SOURCE_LABELS[source]
        st.caption(f"{icon} {label} — *{reasoning}*")

        suggested_csv = intent.get("csv_filename") if source in ("csv", "both") else None

        if source == "csv":
            _run_csv(question, user_id, csv_files, suggested_filename=suggested_csv)
            answer_summary = f"[CSV result] {question}"

        elif source == "pdf":
            _run_pdf(question, user_id)
            answer_summary = f"[Document result] {question}"

        else:  # both — scope each question to its own source
            csv_question = f"Using only the structured CSV data available, answer this: {question}"
            with st.expander("📊 From CSV data", expanded=True):
                _run_csv(csv_question, user_id, csv_files, suggested_filename=suggested_csv)
            with st.expander("📄 From documents", expanded=True):
                _run_pdf(question, user_id)
            answer_summary = f"[CSV + Document result] {question}"

        st.session_state["ask_history"].append({
            "question": question,
            "source": source,
            "answer_summary": answer_summary,
        })
