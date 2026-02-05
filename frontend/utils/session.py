"""Session state initialization and helper functions.

Provides utilities for managing authentication state in Streamlit:
- Session state initialization with auth-related keys
- User info extraction from JWT tokens
- Token expiry checking without verification
- Auth state cleanup on logout
"""

from datetime import datetime, timezone
from typing import Optional

import jwt
import streamlit as st


def init_session_state() -> None:
    """Initialize all auth-related session state keys with defaults.

    Should be called at the start of the app to ensure all keys exist.
    Uses setdefault to avoid overwriting existing values on rerun.
    """
    # Authentication status
    if "is_authenticated" not in st.session_state:
        st.session_state.is_authenticated = False

    # JWT tokens
    if "access_token" not in st.session_state:
        st.session_state.access_token = None

    if "refresh_token" not in st.session_state:
        st.session_state.refresh_token = None

    # Decoded user info from JWT
    if "user_info" not in st.session_state:
        st.session_state.user_info = None

    # Session type: "anonymous" or "authenticated"
    if "session_type" not in st.session_state:
        st.session_state.session_type = "anonymous"


def get_user_info() -> dict:
    """Return user details from session state.

    Extracts info from stored JWT claims or returns anonymous defaults.

    Returns:
        Dict with email, user_id, role, session_type.
    """
    if st.session_state.get("is_authenticated") and st.session_state.get("user_info"):
        user_info = st.session_state.user_info
        return {
            "email": user_info.get("sub", "Unknown"),
            "user_id": user_info.get("user_id", "N/A"),
            "role": user_info.get("role", "user"),
            "session_type": "authenticated",
        }

    # Anonymous user defaults
    return {
        "email": "Anonymous",
        "user_id": "N/A",
        "role": "anonymous",
        "session_type": "anonymous",
    }


def decode_token_claims(token: str) -> Optional[dict]:
    """Decode JWT token to extract claims without signature verification.

    This is safe because we're just reading the claims, not validating.
    Backend already verified the token before sending it.

    Args:
        token: JWT token string.

    Returns:
        Dict of token claims, or None if token is invalid.
    """
    try:
        return jwt.decode(token, options={"verify_signature": False})
    except jwt.DecodeError:
        return None
    except Exception:
        return None


def is_token_expired(token: str) -> bool:
    """Check if JWT token is expired without signature verification.

    Decodes the token and compares exp claim to current UTC time.

    Args:
        token: JWT token string.

    Returns:
        True if token is expired or invalid, False if still valid.
    """
    if not token:
        return True

    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        exp = payload.get("exp")
        if not exp:
            return True

        # Compare expiry to current UTC time
        exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
        return exp_datetime < datetime.now(timezone.utc)
    except jwt.DecodeError:
        return True
    except Exception:
        return True


def get_token_expiry_seconds(token: str) -> int:
    """Return seconds until token expiry.

    Args:
        token: JWT token string.

    Returns:
        Seconds until expiry (positive), or 0 if expired/invalid.
    """
    if not token:
        return 0

    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        exp = payload.get("exp")
        if not exp:
            return 0

        exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
        remaining = exp_datetime - datetime.now(timezone.utc)

        # Return seconds, minimum 0
        return max(0, int(remaining.total_seconds()))
    except jwt.DecodeError:
        return 0
    except Exception:
        return 0


def clear_auth_state() -> None:
    """Reset all auth-related session state keys to defaults.

    Called on logout or when session becomes invalid.
    """
    st.session_state.is_authenticated = False
    st.session_state.access_token = None
    st.session_state.refresh_token = None
    st.session_state.user_info = None
    st.session_state.session_type = "anonymous"


def set_auth_state(access_token: str, refresh_token: str) -> None:
    """Set authentication state from token pair.

    Decodes the access token to extract user info and updates all
    auth-related session state keys.

    Args:
        access_token: JWT access token.
        refresh_token: JWT refresh token.
    """
    # Decode token to get user info
    user_info = decode_token_claims(access_token)

    if user_info:
        st.session_state.is_authenticated = True
        st.session_state.access_token = access_token
        st.session_state.refresh_token = refresh_token
        st.session_state.user_info = user_info
        st.session_state.session_type = "authenticated"
    else:
        # Token decode failed, clear state
        clear_auth_state()


def render_user_info() -> None:
    """Render user info widget in the sidebar.

    Shows different content based on authentication state:
    - Authenticated: email, role, session type, logout button
    - Anonymous: anonymous session info, login hint

    Must be called after init_session_state() and imports handle_logout
    dynamically to avoid circular imports.
    """
    # Import handle_logout here to avoid circular import
    # (auth.py imports from session.py)
    from utils.auth import handle_logout

    with st.sidebar:
        st.markdown("### User Info")

        if st.session_state.get("is_authenticated"):
            user_info = st.session_state.get("user_info", {})
            email = user_info.get("sub", "Unknown")
            role = user_info.get("role", "user")

            st.markdown(f"**Email:** {email}")
            st.markdown(f"**Role:** {role}")
            st.markdown("**Session:** Authenticated")

            st.button("Logout", on_click=handle_logout, key="sidebar_logout")
        else:
            st.markdown("**Session:** Anonymous")
            st.caption("Login to save your data permanently")
