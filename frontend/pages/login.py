"""Login page for user authentication.

Uses callback-based pattern (Pattern 3) to prevent infinite rerun loops:
- Form inputs use key= to bind values to session_state
- Button uses on_click callback instead of inline logic
- Errors stored in session_state and displayed after button

Critical patterns:
- NEVER use: if st.button("Login"): inline_logic()  # causes rerun loop
- ALWAYS use: st.button("Login", on_click=handle_login)  # callback pattern
- NEVER call st.rerun() - Streamlit auto-reruns after callback
"""

import streamlit as st

from utils.auth import handle_login

# Redirect if already logged in
if st.session_state.get("is_authenticated"):
    st.switch_page("pages/home.py")

st.title("Login")

# Form inputs bound to session_state keys
st.text_input("Email", key="login_email")
st.text_input("Password", type="password", key="login_password")

# Button with on_click callback (NOT inline if st.button() logic)
st.button("Login", on_click=handle_login)

# Display error if any (set by handle_login callback)
if st.session_state.get("login_error"):
    st.error(st.session_state.login_error)
    # Clear error after displaying so it doesn't persist
    del st.session_state.login_error

# Navigation hint
st.markdown("---")
st.info("Don't have an account? Go to Register page.")
