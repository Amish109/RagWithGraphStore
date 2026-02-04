---
phase: 01-foundation-core-rag
plan: 04
subsystem: api, document-processing
tags: [pymupdf4llm, python-docx, langchain-text-splitters, fastapi-background-tasks, semantic-chunking]

# Dependency graph
requires:
  - phase: 01-02
    provides: JWT authentication with get_current_user dependency
  - phase: 01-03
    provides: generate_embeddings async function for vector generation
  - phase: 01-01
    provides: Neo4j schema (User, Document, Chunk nodes), Qdrant collection with payload indexes
provides:
  - PDF extraction using pymupdf4llm (clean Markdown output)
  - DOCX extraction using python-docx (paragraphs and tables)
  - Semantic chunking with RecursiveCharacterTextSplitter
  - Async document processing pipeline for background execution
  - Dual-write indexing to Neo4j (metadata) and Qdrant (vectors)
  - POST /api/v1/documents/upload endpoint with auth
  - GET /api/v1/documents/ endpoint for listing user documents
affects: [02-multi-user, query-endpoints, document-management]

# Tech tracking
tech-stack:
  added: [langchain-text-splitters]
  patterns: [background-task-processing, dual-store-indexing, shared-uuid-linkage]

key-files:
  created:
    - backend/app/services/document_processor.py
    - backend/app/services/indexing_service.py
    - backend/app/api/documents.py
    - backend/app/models/document.py
  modified:
    - backend/app/db/qdrant_client.py
    - backend/app/models/schemas.py
    - backend/app/main.py
    - backend/requirements.txt

key-decisions:
  - "pymupdf4llm for PDF extraction (Markdown output preserves structure for better chunking)"
  - "RecursiveCharacterTextSplitter with semantic separators (prevents Pitfall #2)"
  - "Shared UUIDs between Neo4j chunks and Qdrant vectors for cross-referencing"
  - "Background task processing to avoid blocking API (prevents Pitfall #7)"
  - "user_id in all Qdrant payloads for multi-tenant filtering (prevents Pitfall #6)"

patterns-established:
  - "Dual-store pattern: Neo4j for metadata/relationships, Qdrant for vectors, linked by UUID"
  - "Background processing: FastAPI BackgroundTasks for async document pipeline"
  - "Multi-tenant isolation: user_id filter in all document queries"

# Metrics
duration: 4min
completed: 2026-02-04
---

# Phase 01 Plan 04: Document Upload Pipeline Summary

**PDF/DOCX upload with semantic chunking and dual-write to Neo4j (metadata) and Qdrant (vectors) via background processing**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-04T12:46:33Z
- **Completed:** 2026-02-04T12:50:49Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments

- PDF text extraction using pymupdf4llm with Markdown output for structure preservation
- DOCX text extraction handling paragraphs and tables with semantic boundaries
- Semantic chunking using RecursiveCharacterTextSplitter (respects paragraph/sentence boundaries)
- Async document processing pipeline running in background tasks
- Dual-store indexing with shared UUIDs linking Neo4j chunks to Qdrant vectors
- Document upload endpoint with file type and size validation

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement PDF/DOCX parsing with semantic chunking** - `f739b0f` (feat)
2. **Task 2: Implement dual-write indexing and upload endpoint** - `2a4b12e` (feat)

## Files Created/Modified

- `backend/app/services/document_processor.py` - PDF/DOCX extraction and semantic chunking pipeline
- `backend/app/services/indexing_service.py` - Dual-write to Neo4j and Qdrant
- `backend/app/api/documents.py` - Upload and list endpoints with auth
- `backend/app/models/document.py` - Document retrieval with multi-tenant filtering
- `backend/app/db/qdrant_client.py` - Added upsert_chunks for vector storage
- `backend/app/models/schemas.py` - Added DocumentUploadResponse and DocumentInfo
- `backend/app/main.py` - Wired documents router
- `backend/requirements.txt` - Added langchain-text-splitters

## Decisions Made

- **pymupdf4llm over PyPDF2:** Outputs clean Markdown preserving document structure (headings, lists, tables), which improves semantic chunking quality
- **RecursiveCharacterTextSplitter:** Uses ordered separators (\n\n, \n, ". ", " ", "") to respect semantic boundaries, preventing mid-sentence splits
- **Shared UUID pattern:** Same UUID used for Neo4j Chunk.embedding_id and Qdrant point ID, enabling cross-store lookups
- **Background task processing:** Uses FastAPI BackgroundTasks for async pipeline execution, returning immediately with "processing" status

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed langchain-text-splitters dependency**
- **Found during:** Task 1 (semantic chunking implementation)
- **Issue:** RecursiveCharacterTextSplitter not available in langchain or langchain-core
- **Fix:** Installed langchain-text-splitters package and added to requirements.txt
- **Files modified:** backend/requirements.txt
- **Verification:** Import succeeds, chunk_text function works
- **Committed in:** f739b0f (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Dependency was necessary for semantic chunking. No scope creep.

## Issues Encountered

None - plan executed as specified after resolving the dependency.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Document upload pipeline complete and ready for use
- Query endpoints can now search uploaded documents (planned for Phase 1 completion or Phase 2)
- Multi-tenant filtering in place via user_id in Qdrant payloads
- **Phase 1 Foundation complete** - all 4 plans executed

---
*Phase: 01-foundation-core-rag*
*Completed: 2026-02-04*
