"""Home page for authenticated users.

Shows welcome message and user information.
Placeholder for upcoming features (document upload, RAG query).
"""

import streamlit as st

st.title("Home")

if st.session_state.get("user_info"):
    email = st.session_state.user_info.get("sub", "User")
    role = st.session_state.user_info.get("role", "user")
    st.success(f"Welcome, {email}!")
    st.write(f"**Role:** {role}")
    st.write(f"**Session:** {st.session_state.get('session_type', 'unknown')}")
else:
    st.write("Welcome! You're browsing anonymously.")

st.markdown("---")
st.info("Document upload coming in Phase 8")
st.info("RAG Query coming in Phase 9")
