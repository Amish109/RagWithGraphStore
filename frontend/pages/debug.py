"""Debug panel for development and testing.

Shows JWT token details, session state, and useful debugging information.
Requires authentication to view - helps verify auth flows work correctly.
"""

import streamlit as st
import jwt
from datetime import datetime, timezone

st.title("Debug Panel")

# Auth guard - require login to view debug info
if not st.session_state.get("is_authenticated"):
    st.warning("Login required to view debug info")
    st.stop()

st.subheader("JWT Token Info")

# Decode access token without validation (just reading claims)
access_token = st.session_state.get("access_token")
if access_token:
    payload = jwt.decode(
        access_token,
        options={"verify_signature": False}
    )

    col1, col2 = st.columns(2)

    with col1:
        st.metric("User ID", payload.get("user_id", "N/A"))
        st.metric("Role", payload.get("role", "user"))

    with col2:
        # Token expiry countdown
        exp_timestamp = payload.get("exp")
        if exp_timestamp:
            exp_dt = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            remaining = exp_dt - datetime.now(timezone.utc)
            if remaining.total_seconds() > 0:
                mins = int(remaining.total_seconds() // 60)
                secs = int(remaining.total_seconds() % 60)
                st.metric("Token Expires In", f"{mins}m {secs}s")
            else:
                st.metric("Token Expires In", "EXPIRED", delta="-expired")
        else:
            st.metric("Token Expires In", "N/A")

        # Issued at timestamp
        iat_timestamp = payload.get("iat")
        if iat_timestamp:
            iat_dt = datetime.fromtimestamp(iat_timestamp, tz=timezone.utc)
            st.metric("Issued At", iat_dt.strftime("%H:%M:%S"))
        else:
            st.metric("Issued At", "N/A")
else:
    st.warning("No access token available")
    payload = {}

st.subheader("Session State")

# Show key session values in structured format
st.json({
    "is_authenticated": st.session_state.get("is_authenticated"),
    "session_type": st.session_state.get("session_type", "unknown"),
    "user_email": st.session_state.get("user_info", {}).get("sub", "N/A"),
})

# Raw access token (expandable)
with st.expander("Raw Access Token"):
    st.code(st.session_state.get("access_token", "No token"), language="text")

# Decoded payload (expandable)
with st.expander("Decoded Payload"):
    if payload:
        st.json(payload)
    else:
        st.write("No payload to display")
