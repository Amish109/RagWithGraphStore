"""Home page with document upload and chat.

Available to all users (anonymous and authenticated).
- Documents tab: upload PDF/DOCX, view/delete documents
- Chat tab: ask questions about uploaded documents with streaming responses
"""

import json
import time

import streamlit as st

from utils.api_client import (
    delete_document,
    get_document_status,
    list_documents,
    query_documents,
    query_documents_stream,
    upload_document,
)

st.title("RAG with Memory")

# Show session info
if st.session_state.get("is_authenticated"):
    email = st.session_state.user_info.get("sub", "User")
    st.caption(f"Logged in as **{email}**")
else:
    st.caption("Browsing as **anonymous** — login to save your data permanently")

# --- Tabs ---
doc_tab, chat_tab = st.tabs(["Documents", "Chat"])

# =============================================================================
# Documents Tab
# =============================================================================
with doc_tab:
    # File uploader
    uploaded_file = st.file_uploader(
        "Upload a document (PDF or DOCX)",
        type=["pdf", "docx"],
        help="Max 50MB. Supported formats: PDF, DOCX",
    )

    if uploaded_file is not None:
        if st.button("Upload", type="primary"):
            file_bytes = uploaded_file.getvalue()
            content_type = uploaded_file.type or "application/pdf"

            with st.spinner("Uploading..."):
                result = upload_document(file_bytes, uploaded_file.name, content_type)

            if result:
                doc_id = result["document_id"]
                st.success(f"Uploaded **{result['filename']}** — processing started")

                # Poll for processing status
                status_container = st.empty()
                progress_bar = st.progress(0)
                while True:
                    status_info = get_document_status(doc_id)
                    if not status_info:
                        status_container.error("Failed to get processing status")
                        break

                    progress = status_info.get("progress", 0)
                    doc_status = status_info.get("status", "unknown")
                    message = status_info.get("message", "")

                    progress_bar.progress(progress / 100)
                    status_container.info(f"**{doc_status}**: {message}")

                    if doc_status == "completed":
                        status_container.success("Document ready!")
                        progress_bar.progress(100)
                        break
                    elif doc_status == "failed":
                        error = status_info.get("error", "Unknown error")
                        status_container.error(f"Processing failed: {error}")
                        break

                    time.sleep(2)

                st.rerun()

    # Document list
    st.markdown("---")
    st.subheader("Your Documents")

    docs = list_documents()
    st.session_state.documents = docs

    if not docs:
        st.info("No documents uploaded yet. Upload a PDF or DOCX to get started.")
    else:
        for doc in docs:
            col1, col2 = st.columns([4, 1])
            with col1:
                chunks = doc.get("chunk_count", "?")
                st.markdown(f"**{doc['filename']}** ({chunks} chunks)")
            with col2:
                if st.button("Delete", key=f"del_{doc['id']}"):
                    if delete_document(doc["id"]):
                        st.success("Deleted")
                        st.rerun()
                    else:
                        st.error("Delete failed")


# =============================================================================
# Chat Tab
# =============================================================================
with chat_tab:
    if not st.session_state.documents and not list_documents():
        st.info("Upload a document first, then ask questions about it here.")
    else:
        # Display chat history
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg.get("citations"):
                    with st.expander("Sources"):
                        for cit in msg["citations"]:
                            score = cit.get("relevance_score", 0)
                            st.caption(
                                f"**{cit['filename']}** (relevance: {score:.0%})"
                            )
                            st.text(cit.get("chunk_text", ""))

        # Chat input
        if prompt := st.chat_input("Ask a question about your documents..."):
            # Add user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Generate response with streaming
            with st.chat_message("assistant"):
                response_placeholder = st.empty()
                citations = []
                full_response = ""

                try:
                    for event_type, data in query_documents_stream(prompt):
                        if event_type == "status":
                            info = json.loads(data)
                            stage = info.get("stage", "")
                            if stage == "retrieving":
                                response_placeholder.markdown(
                                    "_Searching documents..._"
                                )
                            elif stage == "generating":
                                response_placeholder.markdown("_Generating answer..._")

                        elif event_type == "citations":
                            citations = json.loads(data)

                        elif event_type == "token":
                            full_response += data
                            response_placeholder.markdown(full_response + "▌")

                        elif event_type == "done":
                            response_placeholder.markdown(full_response)

                        elif event_type == "error":
                            error_info = json.loads(data)
                            full_response = (
                                f"Error: {error_info.get('message', 'Unknown error')}"
                            )
                            response_placeholder.error(full_response)

                except Exception:
                    # Fallback to non-streaming query
                    response_placeholder.markdown("_Querying..._")
                    result = query_documents(prompt)
                    if result:
                        full_response = result.get("answer", "No answer available.")
                        citations = result.get("citations", [])
                        response_placeholder.markdown(full_response)
                    else:
                        full_response = "Failed to get a response. Please try again."
                        response_placeholder.error(full_response)

                # Show citations
                if citations:
                    with st.expander("Sources"):
                        for cit in citations:
                            score = cit.get("relevance_score", 0)
                            st.caption(
                                f"**{cit['filename']}** (relevance: {score:.0%})"
                            )
                            st.text(cit.get("chunk_text", ""))

                # Save to history
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": full_response,
                        "citations": citations,
                    }
                )
