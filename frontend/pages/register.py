"""Registration page for new user accounts.

Uses callback-based authentication pattern to avoid rerun loops.
Redirects to home if already authenticated.
"""

import streamlit as st
from utils.auth import handle_register

# Redirect if already logged in
if st.session_state.get("is_authenticated"):
    st.switch_page("pages/home.py")

st.title("Register")

st.text_input("Email", key="register_email")
st.text_input("Password", type="password", key="register_password")
st.text_input("Confirm Password", type="password", key="register_password_confirm")
st.button("Register", on_click=handle_register)

# Display error if any
if st.session_state.get("register_error"):
    st.error(st.session_state.register_error)
    del st.session_state.register_error

st.markdown("---")
st.info("Already have an account? Go to Login page.")
