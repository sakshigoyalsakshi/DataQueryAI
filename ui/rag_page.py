import uuid
from datetime import datetime, timezone

import streamlit as st

from data.db import get_conn
from rag.pdf_parser import extract_chunks
from rag.vector_store import add_chunks, delete_doc_chunks
from rag.rag_pipeline import answer_question


def _list_pdfs(user_id: str) -> list[dict]:
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT id, filename, page_count, chunk_count, created_at FROM pdfs WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
    finally:
        conn.close()
    return [{"id": r[0], "filename": r[1], "page_count": r[2], "chunk_count": r[3]} for r in rows]


def _save_pdf_meta(user_id: str, doc_id: str, filename: str, page_count: int, chunk_count: int) -> None:
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO pdfs (id, user_id, filename, page_count, chunk_count, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (doc_id, user_id, filename, page_count, chunk_count, datetime.now(timezone.utc)),
        )
        conn.commit()
    finally:
        conn.close()


def _delete_pdf_meta(doc_id: str) -> None:
    conn = get_conn()
    try:
        conn.execute("DELETE FROM pdfs WHERE id = ?", (doc_id,))
        conn.commit()
    finally:
        conn.close()


def show_rag_page(user_id: str) -> None:
    st.header("Document Q&A")
    st.caption("Upload PDFs and ask questions — answers include page citations.")

    # Upload section
    with st.expander("Upload a PDF", expanded=True):
        uploaded = st.file_uploader("Choose a PDF file", type=["pdf"])
        if uploaded:
            file_key = f"{uploaded.name}_{uploaded.size}"
            if st.session_state.get("last_uploaded_pdf") != file_key:
                with st.spinner("Parsing and indexing PDF..."):
                    try:
                        file_bytes = uploaded.read()
                        chunks = extract_chunks(file_bytes, uploaded.name)
                        if not chunks:
                            st.error("Could not extract text from this PDF. It may be image-based or encrypted.")
                        else:
                            doc_id = str(uuid.uuid4())
                            add_chunks(user_id, chunks, doc_id)
                            page_count = max(c["page"] for c in chunks)
                            _save_pdf_meta(user_id, doc_id, uploaded.name, page_count, len(chunks))
                            st.session_state["last_uploaded_pdf"] = file_key
                            st.success(
                                f"Indexed **{uploaded.name}** — {page_count} pages, {len(chunks)} chunks"
                            )
                            st.rerun()
                    except Exception as e:
                        st.error(f"Failed to process PDF: {e}")

    st.divider()

    # List uploaded PDFs
    pdfs = _list_pdfs(user_id)
    if pdfs:
        st.subheader("Uploaded Documents")
        for pdf in pdfs:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**{pdf['filename']}** — {pdf['page_count']} pages, {pdf['chunk_count']} chunks")
            with col2:
                if st.button("Delete", key=f"delpdf_{pdf['id']}", type="secondary"):
                    delete_doc_chunks(user_id, pdf["id"], pdf["chunk_count"])
                    _delete_pdf_meta(pdf["id"])
                    st.rerun()
        st.divider()
    else:
        st.info("No documents yet. Upload a PDF above to get started.")
        return

    # Q&A section
    st.subheader("Ask a Question")

    if "rag_history" not in st.session_state:
        st.session_state["rag_history"] = []

    # Show conversation history
    for turn in st.session_state["rag_history"]:
        with st.chat_message("user"):
            st.write(turn["question"])
        with st.chat_message("assistant"):
            st.write(turn["answer"])
            if turn["sources"]:
                source_strs = [f"**{s['filename']}**, p.{s['page']}" for s in turn["sources"]]
                st.caption("Sources: " + " · ".join(source_strs))

    # Input
    question = st.chat_input("Ask a question about your documents...")
    if question:
        with st.chat_message("user"):
            st.write(question)
        with st.chat_message("assistant"):
            with st.spinner("Searching documents..."):
                result = answer_question(user_id, question)
            if "error" in result:
                st.error(result["error"])
            else:
                st.write(result["answer"])
                if result["sources"]:
                    source_strs = [f"**{s['filename']}**, p.{s['page']}" for s in result["sources"]]
                    st.caption("Sources: " + " · ".join(source_strs))
                st.session_state["rag_history"].append({
                    "question": question,
                    "answer": result["answer"],
                    "sources": result["sources"],
                })
