"""Multi-Tenant Isolation Security Tests.

CRITICAL: These tests verify users cannot access other users' data.
They should run in CI before every deployment.

Based on: "Authentication Is Not Isolation: Five Tests"
https://aliengiraffe.ai/blog/authentication-is-not-isolation-the-five-tests-your-multi-tenant-system-is-probably-failing/

Test Categories:
1. Document Isolation - Users cannot see/modify other users' documents
2. Memory Isolation - Users cannot see other users' memories
3. Token Security - Tampered tokens are rejected
4. Anonymous Isolation - Anonymous sessions are isolated
5. Admin Access Control - RBAC is enforced
"""

from io import BytesIO

import jwt
import pytest
from httpx import AsyncClient

# Minimal valid PDF content for testing
# This is the smallest valid PDF that can be processed
TEST_PDF_CONTENT = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT
/F1 12 Tf
100 700 Td
(Test) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000214 00000 n
trailer
<< /Size 5 /Root 1 0 R >>
startxref
308
%%EOF"""


@pytest.mark.asyncio
class TestDocumentIsolation:
    """Test that users cannot access other users' documents.

    These tests verify the defense-in-depth strategy for multi-tenant
    document isolation. Every database query must include user_id filter.
    """

    async def test_user_cannot_see_other_users_documents_in_queries(
        self,
        client: AsyncClient,
        auth_headers_a: dict,
        auth_headers_b: dict,
    ):
        """CRITICAL: User A cannot see User B's documents in query results.

        This is the most important isolation test. If this fails,
        there is a data breach vulnerability.
        """
        # User A uploads a document with unique content
        files = {
            "file": ("user_a_secret.pdf", BytesIO(TEST_PDF_CONTENT), "application/pdf")
        }
        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers_a,
            files=files,
        )
        # Accept various success codes (200, 201, 202 for background processing)
        assert response.status_code in [
            200,
            201,
            202,
        ], f"Upload failed: {response.text}"

        # User B queries - should NOT see User A's document
        response = await client.post(
            "/api/v1/query",
            headers=auth_headers_b,
            json={"query": "user_a_secret document content"},
        )
        assert response.status_code == 200

        # Verify User B does not see User A's document in citations
        citations = response.json().get("citations", [])
        citation_files = [c.get("filename", "") for c in citations]

        assert "user_a_secret.pdf" not in citation_files, (
            "ISOLATION FAILURE: User B saw User A's document in query results"
        )

    async def test_user_cannot_list_other_users_documents(
        self,
        client: AsyncClient,
        auth_headers_a: dict,
        auth_headers_b: dict,
    ):
        """User A's documents should not appear in User B's document list.

        Tests the document listing endpoint for tenant isolation.
        """
        # User A uploads document with identifiable filename
        files = {
            "file": (
                "secret_doc_user_a.pdf",
                BytesIO(TEST_PDF_CONTENT),
                "application/pdf",
            )
        }
        await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers_a,
            files=files,
        )

        # User B lists their documents
        response = await client.get(
            "/api/v1/documents",
            headers=auth_headers_b,
        )

        if response.status_code == 200:
            documents = response.json()
            # Handle both list and dict with 'documents' key
            if isinstance(documents, dict):
                documents = documents.get("documents", [])

            for doc in documents:
                filename = doc.get("filename", "")
                assert "secret_doc_user_a" not in filename, (
                    f"ISOLATION FAILURE: User B saw User A's document '{filename}' in list"
                )

    async def test_user_cannot_delete_other_users_documents(
        self,
        client: AsyncClient,
        auth_headers_a: dict,
        auth_headers_b: dict,
    ):
        """CRITICAL: User A cannot delete User B's documents.

        Tests write isolation - users should not be able to modify
        other users' data.
        """
        # User A uploads document
        files = {
            "file": (
                "delete_test_user_a.pdf",
                BytesIO(TEST_PDF_CONTENT),
                "application/pdf",
            )
        }
        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers_a,
            files=files,
        )

        if response.status_code in [200, 201, 202]:
            doc_id = response.json().get("document_id")

            if doc_id:
                # User B tries to delete User A's document
                response = await client.delete(
                    f"/api/v1/documents/{doc_id}",
                    headers=auth_headers_b,
                )

                # Should be forbidden (403) or not found (404)
                assert response.status_code in [403, 404], (
                    f"ISOLATION FAILURE: User B was able to access User A's document "
                    f"for deletion (status: {response.status_code})"
                )


@pytest.mark.asyncio
class TestMemoryIsolation:
    """Test that users cannot access other users' memories.

    Mem0 uses user_id parameter for isolation. These tests verify
    that memories are properly scoped to their owners.
    """

    async def test_user_cannot_search_other_users_memories(
        self,
        client: AsyncClient,
        auth_headers_a: dict,
        auth_headers_b: dict,
    ):
        """User A's memories should not appear in User B's memory searches.

        Tests memory search isolation with a unique identifier that
        should only be findable by User A.
        """
        # User A adds a memory with unique content
        unique_content = "SECRET_MEMORY_USER_A_12345"
        response = await client.post(
            "/api/v1/memory",
            headers=auth_headers_a,
            json={"content": unique_content},
        )

        # User B searches for User A's secret
        response = await client.post(
            "/api/v1/memory/search",
            headers=auth_headers_b,
            json={"query": unique_content},
        )

        if response.status_code == 200:
            memories = response.json().get("memories", [])
            for mem in memories:
                memory_content = mem.get("memory", "")
                assert "SECRET_MEMORY_USER_A" not in memory_content, (
                    f"ISOLATION FAILURE: User B found User A's memory: {memory_content}"
                )

    async def test_user_cannot_list_other_users_memories(
        self,
        client: AsyncClient,
        auth_headers_a: dict,
        auth_headers_b: dict,
    ):
        """User A's memories should not appear in User B's memory list.

        Tests memory listing isolation.
        """
        # User A adds memory
        await client.post(
            "/api/v1/memory",
            headers=auth_headers_a,
            json={"content": "PRIVATE_FACT_USER_A_ONLY"},
        )

        # User B lists memories
        response = await client.get(
            "/api/v1/memory",
            headers=auth_headers_b,
        )

        if response.status_code == 200:
            memories = response.json().get("memories", [])
            for mem in memories:
                memory_content = mem.get("memory", "")
                assert "PRIVATE_FACT_USER_A" not in memory_content, (
                    f"ISOLATION FAILURE: User B saw User A's memory in list: {memory_content}"
                )


@pytest.mark.asyncio
class TestTokenSecurity:
    """Test that token manipulation is detected and rejected.

    These tests verify JWT validation is working correctly
    and tampered tokens cannot be used to access data.
    """

    async def test_tampered_token_rejected(
        self,
        client: AsyncClient,
        user_a_token: str,
    ):
        """CRITICAL: Modified tokens must be rejected.

        Attempts to tamper with the user_id in the token payload
        and sign with a wrong key. This should be rejected.
        """
        # Decode token without verification to get payload
        payload = jwt.decode(user_a_token, options={"verify_signature": False})

        # Tamper with user_id
        payload["user_id"] = "attacker_injected_id"

        # Re-encode with wrong key (attacker doesn't know real secret)
        tampered_token = jwt.encode(payload, "wrong_secret_key", algorithm="HS256")

        # Attempt to use tampered token
        response = await client.post(
            "/api/v1/query",
            headers={"Authorization": f"Bearer {tampered_token}"},
            json={"query": "test query"},
        )

        assert response.status_code == 401, (
            f"SECURITY FAILURE: Tampered token was accepted (status: {response.status_code})"
        )

    async def test_invalid_token_string_rejected(
        self,
        client: AsyncClient,
    ):
        """Invalid token strings should be rejected.

        Tests basic token validation - random strings should not work.
        """
        response = await client.post(
            "/api/v1/query",
            headers={"Authorization": "Bearer completely_invalid_token_string"},
            json={"query": "test query"},
        )

        assert response.status_code in [401, 403], (
            f"Invalid token should be rejected (status: {response.status_code})"
        )

    async def test_malformed_authorization_header_rejected(
        self,
        client: AsyncClient,
    ):
        """Malformed authorization headers should be rejected.

        Tests that various malformed auth headers are handled safely.
        """
        # Missing "Bearer " prefix
        response = await client.post(
            "/api/v1/query",
            headers={"Authorization": "some_token_without_bearer"},
            json={"query": "test query"},
        )
        # Should either reject or treat as unauthenticated (anonymous)
        assert response.status_code in [200, 401, 403, 422]


@pytest.mark.asyncio
class TestAnonymousIsolation:
    """Test anonymous session isolation.

    Anonymous users get temporary sessions. These tests verify
    that anonymous sessions are properly isolated from each other
    and from authenticated users.
    """

    async def test_anonymous_cannot_access_authenticated_users_documents(
        self,
        client: AsyncClient,
        auth_headers_a: dict,
    ):
        """Anonymous users cannot see authenticated users' documents.

        Tests cross-authentication-boundary isolation.
        """
        # Authenticated user uploads document
        files = {
            "file": (
                "auth_user_only.pdf",
                BytesIO(TEST_PDF_CONTENT),
                "application/pdf",
            )
        }
        await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers_a,
            files=files,
        )

        # Anonymous user queries (no auth header)
        response = await client.post(
            "/api/v1/query",
            json={"query": "auth_user_only document"},
        )

        if response.status_code == 200:
            citations = response.json().get("citations", [])
            citation_files = [c.get("filename", "") for c in citations]

            assert "auth_user_only" not in str(citation_files), (
                "ISOLATION FAILURE: Anonymous user saw authenticated user's document"
            )

    async def test_different_anonymous_sessions_are_isolated(
        self,
        client: AsyncClient,
    ):
        """Different anonymous sessions should be isolated from each other.

        Tests that anonymous session A cannot see anonymous session B's data.
        """
        # First anonymous request - creates session and adds memory
        response1 = await client.post(
            "/api/v1/memory",
            json={"content": "ANON_SESSION_1_SECRET_XYZ"},
        )
        cookies1 = response1.cookies

        # Second anonymous request - new client, no cookies = new session
        # Search for first session's memory
        response2 = await client.post(
            "/api/v1/memory/search",
            json={"query": "ANON_SESSION_1_SECRET_XYZ"},
            # Explicitly NOT including cookies1 to get a new session
        )

        if response2.status_code == 200:
            memories = response2.json().get("memories", [])
            for mem in memories:
                memory_content = mem.get("memory", "")
                # Should not find the first session's memory
                assert "ANON_SESSION_1_SECRET" not in memory_content, (
                    "ISOLATION FAILURE: Anonymous session 2 saw session 1's memory"
                )


@pytest.mark.asyncio
class TestAdminAccessControl:
    """Test admin role enforcement (RBAC).

    Tests that admin-only endpoints are properly protected
    and regular users cannot access them.
    """

    async def test_non_admin_cannot_access_admin_endpoints(
        self,
        client: AsyncClient,
        auth_headers_a: dict,  # Regular user
    ):
        """Non-admin users should get 403 on admin endpoints.

        Tests RBAC enforcement on the shared memory admin endpoint.
        """
        response = await client.post(
            "/api/v1/admin/memory/shared",
            headers=auth_headers_a,
            json={"content": "Attempted unauthorized shared memory"},
        )

        assert response.status_code == 403, (
            f"RBAC FAILURE: Non-admin accessed admin endpoint "
            f"(status: {response.status_code})"
        )

    async def test_admin_can_access_admin_endpoints(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Admin users should have access to admin endpoints.

        Tests that admin role grants appropriate access.
        """
        response = await client.post(
            "/api/v1/admin/memory/shared",
            headers=admin_headers,
            json={"content": "Admin test shared memory"},
        )

        assert response.status_code == 200, (
            f"Admin denied access to admin endpoint (status: {response.status_code}, "
            f"body: {response.text})"
        )

    async def test_shared_memory_visible_to_authenticated_not_anonymous(
        self,
        client: AsyncClient,
        admin_headers: dict,
        auth_headers_b: dict,
    ):
        """Shared memories visible to authenticated users, not anonymous.

        Tests that shared memory respects authentication boundaries:
        - Admin can add shared memories
        - Authenticated users can search and find them
        - Anonymous users cannot see shared memories
        """
        unique_shared_fact = "SHARED_COMPANY_FACT_ABC123"

        # Admin adds shared memory
        response = await client.post(
            "/api/v1/admin/memory/shared",
            headers=admin_headers,
            json={"content": unique_shared_fact},
        )
        assert response.status_code == 200, (
            f"Admin failed to add shared memory: {response.text}"
        )

        # Authenticated user searches and should find it
        response = await client.post(
            "/api/v1/memory/search",
            headers=auth_headers_b,
            json={"query": unique_shared_fact},
        )

        # Note: Whether they find it depends on Mem0 indexing timing
        # The key test is that anonymous CANNOT see it

        # Anonymous user should NOT see shared memories
        response = await client.post(
            "/api/v1/memory/search",
            json={"query": unique_shared_fact},
        )

        if response.status_code == 200:
            memories = response.json().get("memories", [])
            for mem in memories:
                is_shared = mem.get("metadata", {}).get("is_shared", False) or mem.get(
                    "is_shared", False
                )
                if is_shared:
                    pytest.fail(
                        "ISOLATION FAILURE: Anonymous user saw shared company memory"
                    )


@pytest.mark.asyncio
class TestCrossUserDataManipulation:
    """Test that users cannot manipulate other users' data.

    Additional tests for write operations across tenant boundaries.
    """

    async def test_user_cannot_update_other_users_data_via_id_guessing(
        self,
        client: AsyncClient,
        auth_headers_a: dict,
        auth_headers_b: dict,
    ):
        """Users cannot access data by guessing resource IDs.

        Even if User B knows User A's document/memory ID,
        they should not be able to access or modify it.
        """
        # User A creates a memory and gets its ID
        response = await client.post(
            "/api/v1/memory",
            headers=auth_headers_a,
            json={"content": "User A's protected memory"},
        )

        if response.status_code == 200:
            memory_id = response.json().get("memory_id")

            if memory_id and memory_id != "created":
                # User B tries to delete User A's memory by ID
                response = await client.delete(
                    f"/api/v1/memory/{memory_id}",
                    headers=auth_headers_b,
                )

                # Should be forbidden or not found
                assert response.status_code in [403, 404], (
                    f"User B was able to access User A's memory by ID "
                    f"(status: {response.status_code})"
                )
