"""Main Streamlit application entry point.

Handles:
- Environment variable loading
- Session state initialization
- Dynamic navigation based on authentication state
- Sidebar user info rendering

Critical patterns (Pitfall #6 prevention):
- st.navigation() is called EXACTLY ONCE here
- NEVER call st.navigation() in individual page files
- Use st.switch_page() for programmatic navigation within pages
"""

import streamlit as st
from dotenv import load_dotenv

# Load environment variables (API_BASE_URL, etc.)
load_dotenv()

# Initialize session state before any page logic
from utils.session import init_session_state, render_user_info

init_session_state()

# Define all available pages
login_page = st.Page("pages/login.py", title="Login", icon=":material/login:")
register_page = st.Page("pages/register.py", title="Register", icon=":material/person_add:")
home_page = st.Page("pages/home.py", title="Home", icon=":material/home:")
debug_page = st.Page("pages/debug.py", title="Debug", icon=":material/bug_report:")

# Build navigation based on authentication state
# Only authenticated users see Main and Tools sections
# Anonymous users only see auth pages
if st.session_state.get("is_authenticated"):
    pg = st.navigation({
        "Main": [home_page],
        "Tools": [debug_page],
    })
else:
    pg = st.navigation([login_page, register_page])

# Render sidebar user info (shows logout button for authenticated users)
render_user_info()

# Run the selected page
pg.run()
