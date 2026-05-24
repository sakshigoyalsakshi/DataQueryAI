import os

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Must be first Streamlit call
st.set_page_config(
    page_title="DataQuery AI",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

from streamlit_cookies_controller import CookieController
from auth.auth import create_demo_user_if_missing, decode_token
from data.db import init_db
from data.csv_manager import preload_sample_data
from ui.login_page import show_login_page
from ui.upload_page import show_upload_page
from ui.query_page import show_query_page
from ui.rag_page import show_rag_page
from ui.ask_page import show_ask_page

SAMPLE_CSV = os.path.join(os.path.dirname(__file__), "sample_data", "ecommerce_sales.csv")
SAMPLE_PDF = os.path.join(os.path.dirname(__file__), "sample_data", "business_report.pdf")
COOKIE_NAME = "dq_auth_token"


def _preload_sample_pdf(user_id: str, pdf_path: str) -> None:
    from data.db import get_conn
    from rag.pdf_parser import extract_chunks
    from rag.vector_store import add_chunks
    from ui.rag_page import _save_pdf_meta
    import uuid
    from datetime import datetime, timezone

    filename = os.path.basename(pdf_path)
    conn = get_conn()
    try:
        existing = conn.execute(
            "SELECT id FROM pdfs WHERE user_id = ? AND filename = ?", (user_id, filename)
        ).fetchone()
        if existing:
            return
    finally:
        conn.close()

    with open(pdf_path, "rb") as f:
        file_bytes = f.read()
    chunks = extract_chunks(file_bytes, filename)
    if chunks:
        doc_id = str(uuid.uuid4())
        add_chunks(user_id, chunks, doc_id)
        page_count = max(c["page"] for c in chunks)
        _save_pdf_meta(user_id, doc_id, filename, page_count, len(chunks))


@st.cache_resource
def startup() -> None:
    """Run once: init DB, ensure demo user and sample data exist."""
    init_db()
    create_demo_user_if_missing()
    from data.db import get_conn
    conn = get_conn()
    row = conn.execute("SELECT id FROM users WHERE email = ?", ("demo@example.com",)).fetchone()
    conn.close()
    if row:
        demo_id = row[0]
        if os.path.exists(SAMPLE_CSV):
            preload_sample_data(demo_id, SAMPLE_CSV)
        if os.path.exists(SAMPLE_PDF):
            _preload_sample_pdf(demo_id, SAMPLE_PDF)


startup()

controller = CookieController()


def get_current_user() -> "dict | None":
    # Check session state first (fast path)
    token = st.session_state.get("token")

    # Fall back to cookie on fresh load / refresh
    if not token:
        try:
            token = controller.get(COOKIE_NAME)
        except Exception:
            token = None
        if token:
            st.session_state["token"] = token
            st.rerun()  # cookie just became available; re-render as authenticated user

    if not token:
        return None
    return decode_token(token)


def main() -> None:
    user = get_current_user()

    if not user:
        show_login_page(on_login=lambda token: _handle_login(token))
        return

    # Sidebar
    with st.sidebar:
        st.title("📊 DataQuery AI")
        st.caption(f"Logged in as **{user['email']}**")
        st.divider()
        page = st.radio(
            "Navigate",
            ["Ask Anything", "Query Data", "My Datasets", "Document Q&A"],
            label_visibility="collapsed",
        )
        st.divider()
        if st.button("Logout", use_container_width=True):
            controller.remove(COOKIE_NAME)
            st.session_state.clear()
            st.rerun()

    user_id = user["sub"]

    if page == "Ask Anything":
        show_ask_page(user_id)
    elif page == "Query Data":
        show_query_page(user_id)
    elif page == "My Datasets":
        show_upload_page(user_id)
    elif page == "Document Q&A":
        show_rag_page(user_id)


def _handle_login(token: str) -> None:
    st.session_state["token"] = token
    controller.set(COOKIE_NAME, token, max_age=86400)  # 24 hours
    st.rerun()


main()
