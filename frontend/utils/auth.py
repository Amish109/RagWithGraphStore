"""Authentication callback handlers for Streamlit pages.

Provides callbacks for login/register buttons using Pattern 3 (callback-based)
to prevent infinite rerun loops. Callbacks read from session_state keys set
by form inputs and update session_state with results.

Critical patterns:
- Read form values from session_state keys (set by text_input key= param)
- Update session_state with auth result
- NEVER call st.rerun() - Streamlit auto-reruns after callback
"""

import streamlit as st

from utils.api_client import login
from utils.session import decode_token_claims, set_auth_state


def handle_login() -> None:
    """Login callback for button on_click.

    Reads credentials from session_state keys set by text_input widgets,
    calls the login API, and updates session state with result.

    Session state keys read:
        - login_email: Email from text_input
        - login_password: Password from text_input

    Session state keys set on success:
        - is_authenticated: True
        - access_token: JWT access token
        - refresh_token: JWT refresh token
        - user_info: Decoded token claims
        - session_type: "authenticated"

    Session state keys set on failure:
        - login_error: Error message string

    Note: Does NOT call st.rerun() - Streamlit auto-reruns after callback.
    """
    # Read credentials from session_state (set by text_input key=)
    email = st.session_state.get("login_email", "").strip()
    password = st.session_state.get("login_password", "")

    # Validate inputs
    if not email:
        st.session_state.login_error = "Email is required"
        return

    if not password:
        st.session_state.login_error = "Password is required"
        return

    # Call login API (synchronous wrapper around async)
    result = login(email, password)

    if result:
        # Login succeeded - update auth state using existing helper
        access_token = result.get("access_token")
        refresh_token = result.get("refresh_token")

        if access_token and refresh_token:
            # Use set_auth_state from session.py which handles all state updates
            set_auth_state(access_token, refresh_token)
            # Clear any previous error
            if "login_error" in st.session_state:
                del st.session_state.login_error
        else:
            st.session_state.login_error = "Invalid response from server"
    # Note: If result is None, api_client.login() already displayed error via st.error()
    # We set a generic error in session_state for consistent handling
    elif "login_error" not in st.session_state:
        st.session_state.login_error = "Login failed. Please check your credentials."
