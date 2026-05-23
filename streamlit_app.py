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

from auth.auth import create_demo_user_if_missing, decode_token
from data.db import init_db
from data.csv_manager import preload_sample_data
from ui.login_page import show_login_page
from ui.upload_page import show_upload_page
from ui.query_page import show_query_page
from ui.rag_page import show_rag_page

SAMPLE_CSV = os.path.join(os.path.dirname(__file__), "sample_data", "ecommerce_sales.csv")


@st.cache_resource
def startup() -> None:
    """Run once: init DB, ensure demo user and sample data exist."""
    init_db()
    create_demo_user_if_missing()
    if os.path.exists(SAMPLE_CSV):
        from data.db import get_conn
        # Get demo user id
        conn = get_conn()
        row = conn.execute("SELECT id FROM users WHERE email = ?", ("demo@example.com",)).fetchone()
        conn.close()
        if row:
            preload_sample_data(row[0], SAMPLE_CSV)


startup()


def get_current_user() -> "dict | None":
    token = st.session_state.get("token")
    if not token:
        return None
    return decode_token(token)


def main() -> None:
    user = get_current_user()

    if not user:
        show_login_page()
        return

    # Sidebar
    with st.sidebar:
        st.title("📊 DataQuery AI")
        st.caption(f"Logged in as **{user['email']}**")
        st.divider()
        page = st.radio(
            "Navigate",
            ["Query Data", "My Datasets", "Document Q&A"],
            label_visibility="collapsed",
        )
        st.divider()
        if st.button("Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    user_id = user["sub"]

    if page == "Query Data":
        show_query_page(user_id)
    elif page == "My Datasets":
        show_upload_page(user_id)
    elif page == "Document Q&A":
        show_rag_page(user_id)


main()
