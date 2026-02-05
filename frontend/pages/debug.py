"""Debug page for development and testing.

Shows session state and useful debugging information.
Useful for verifying auth state, tokens, and API responses.
"""

import streamlit as st

st.title("Debug")

st.markdown("### Session State")

# Auth status
st.write("**Authentication:**")
st.write(f"- is_authenticated: `{st.session_state.get('is_authenticated', False)}`")
st.write(f"- session_type: `{st.session_state.get('session_type', 'unknown')}`")

# Token info (show presence, not values for security)
st.write("**Tokens:**")
has_access = bool(st.session_state.get("access_token"))
has_refresh = bool(st.session_state.get("refresh_token"))
st.write(f"- access_token present: `{has_access}`")
st.write(f"- refresh_token present: `{has_refresh}`")

# User info
st.write("**User Info:**")
user_info = st.session_state.get("user_info")
if user_info:
    st.json(user_info)
else:
    st.write("- No user info available")

# Full session state (expandable)
with st.expander("Full Session State (Raw)"):
    # Filter out potentially sensitive data
    safe_state = {}
    for key, value in st.session_state.items():
        if "token" in key.lower() or "password" in key.lower():
            safe_state[key] = "[REDACTED]" if value else None
        else:
            safe_state[key] = value
    st.json(safe_state)
