"""Authentication callback handlers for Streamlit pages.

Provides callback functions for login and registration forms.
These are designed to work with Streamlit's button on_click pattern
to avoid infinite rerun loops (Pitfall #2 from research).

Key patterns:
- Read inputs from session_state keys (set by st.text_input)
- Call API client functions (sync wrappers around async)
- Update session state on success/failure
- NEVER call st.rerun() - let Streamlit handle reruns naturally
"""

import streamlit as st

from utils.api_client import login, register
from utils.session import set_auth_state


def handle_login() -> None:
    """Callback handler for login button.

    Reads email/password from session_state keys set by text inputs.
    Calls login API and updates auth state on success.
    Sets error message on failure for display after rerun.

    Session state inputs:
        - login_email: User's email address
        - login_password: User's password

    Session state outputs (on success):
        - is_authenticated: True
        - access_token: JWT access token
        - refresh_token: JWT refresh token
        - user_info: Decoded token claims

    Session state outputs (on failure):
        - login_error: Error message to display
    """
    email = st.session_state.get("login_email", "")
    password = st.session_state.get("login_password", "")

    # Basic client-side validation
    if not email or not password:
        st.session_state.login_error = "Email and password are required"
        return

    # Call API (sync wrapper handles asyncio.run internally)
    result = login(email, password)

    if result:
        # Success - update auth state with tokens
        access_token = result.get("access_token")
        refresh_token = result.get("refresh_token")

        if access_token and refresh_token:
            set_auth_state(access_token, refresh_token)
            # Clear any previous error
            if "login_error" in st.session_state:
                del st.session_state.login_error
        else:
            st.session_state.login_error = "Invalid response from server"
    # Note: On failure, login() already calls st.error() and returns None
    # We don't need to set login_error here as the error is already shown


def handle_register() -> None:
    """Callback handler for registration button.

    Reads email/password/confirm from session_state keys set by text inputs.
    Validates passwords match before calling API.
    Calls register API and updates auth state on success.
    Sets error message on failure for display after rerun.

    Session state inputs:
        - register_email: User's email address
        - register_password: User's password
        - register_password_confirm: Password confirmation

    Session state outputs (on success):
        - is_authenticated: True
        - access_token: JWT access token
        - refresh_token: JWT refresh token
        - user_info: Decoded token claims

    Session state outputs (on failure):
        - register_error: Error message to display
    """
    email = st.session_state.get("register_email", "")
    password = st.session_state.get("register_password", "")
    password_confirm = st.session_state.get("register_password_confirm", "")

    # Basic client-side validation
    if not email or not password:
        st.session_state.register_error = "Email and password are required"
        return

    # Validate passwords match (client-side validation)
    if password != password_confirm:
        st.session_state.register_error = "Passwords do not match"
        return

    # Call API (sync wrapper handles asyncio.run internally)
    result = register(email, password)

    if result:
        # Success - update auth state with tokens
        access_token = result.get("access_token")
        refresh_token = result.get("refresh_token")

        if access_token and refresh_token:
            set_auth_state(access_token, refresh_token)
            # Clear any previous error
            if "register_error" in st.session_state:
                del st.session_state.register_error
        else:
            st.session_state.register_error = "Invalid response from server"
    # Note: On failure, register() already calls st.error() and returns None
    # We don't need to set register_error here as the error is already shown
