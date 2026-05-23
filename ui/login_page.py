import streamlit as st
from auth.auth import login_user, register_user


def show_login_page() -> None:
    st.title("DataQuery AI")
    st.caption("Ask natural language questions about your CSV data")

    tab_login, tab_register = st.tabs(["Login", "Register"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)

        if submitted:
            if not email or not password:
                st.error("Please enter your email and password.")
            else:
                ok, result = login_user(email, password)
                if ok:
                    st.session_state["token"] = result
                    st.session_state["logged_in"] = True
                    st.rerun()
                else:
                    st.error(result)

        st.info("Demo account: demo@example.com / demo1234")

    with tab_register:
        with st.form("register_form"):
            new_email = st.text_input("Email", key="reg_email")
            new_password = st.text_input("Password", type="password", key="reg_pass")
            confirm = st.text_input("Confirm Password", type="password", key="reg_confirm")
            submitted_reg = st.form_submit_button("Create Account", use_container_width=True)

        if submitted_reg:
            if new_password != confirm:
                st.error("Passwords do not match.")
            else:
                ok, result = register_user(new_email, new_password)
                if ok:
                    st.success("Account created! Please log in.")
                else:
                    st.error(result)
