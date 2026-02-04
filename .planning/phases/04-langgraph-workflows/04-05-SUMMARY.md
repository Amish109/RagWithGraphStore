---
phase: 04-langgraph-workflows
plan: 05
subsystem: api
tags: [fastapi, langgraph, comparison, citations, workflow-api]
dependency-graph:
  requires: ["04-03", "04-04"]
  provides: ["comparison-api-endpoint", "multi-turn-comparison"]
  affects: ["05-differentiation-features"]
tech-stack:
  added: []
  patterns: ["workflow-api-integration", "memory-tracking-per-interaction"]
key-files:
  created:
    - backend/app/api/comparisons.py
  modified:
    - backend/app/models/schemas.py
    - backend/app/main.py
decisions:
  - id: "04-05-01"
    decision: "ComparisonCitation separate from existing Citation"
    rationale: "Different fields needed (chunk_id vs chunk_text, no relevance_score)"
  - id: "04-05-02"
    decision: "Require authentication for comparison endpoint"
    rationale: "Document comparison is resource-intensive; anonymous access deferred"
  - id: "04-05-03"
    decision: "Memory updated after each comparison interaction"
    rationale: "Enables context continuity and summarization in long conversations"
metrics:
  duration: "2 min"
  completed: "2026-02-04"
---

# Phase 4 Plan 05: Document Comparison API Endpoint Summary

REST API endpoint for document comparison using LangGraph workflow with memory integration.

## One-liner

Document comparison API at POST /api/v1/compare integrating LangGraph workflow with per-interaction memory tracking.

## What Was Done

### Task 1: Add comparison schemas to models
- Added `ComparisonRequest` with document_ids (2-5), query, optional session_id
- Added `ComparisonCitation` with document_id, chunk_id, filename, text
- Added `ComparisonResponse` with similarities, differences, insights, citations
- Used Pydantic Field constraints for validation (min/max lengths)
- Commit: `2cee804`

### Task 2: Create comparison API router
- Created `backend/app/api/comparisons.py` with two endpoints:
  - POST `/` - Execute document comparison workflow
  - GET `/{session_id}/state` - Retrieve multi-turn conversation state
- Integrates with `compare_documents` from LangGraph workflow
- Calls `memory_summarizer.add_interaction()` after each comparison
- Returns structured `ComparisonResponse` with citations
- Commit: `010ea58`

### Task 3: Register comparison router in main app
- Imported `comparisons_router` in main.py
- Registered at `/api/v1/compare` prefix with "comparison" tag
- Maintains alphabetical order with other routers
- Commit: `ea42857`

## Files Changed

| File | Action | Purpose |
|------|--------|---------|
| `backend/app/models/schemas.py` | Modified | Added ComparisonRequest, ComparisonCitation, ComparisonResponse |
| `backend/app/api/comparisons.py` | Created | Document comparison API endpoints |
| `backend/app/main.py` | Modified | Register comparison router |

## Decisions Made

1. **ComparisonCitation separate from existing Citation** (04-05-01)
   - Existing `Citation` has `chunk_text` and `relevance_score` for queries
   - New `ComparisonCitation` has `chunk_id` and fixed text max length
   - Avoids breaking existing query endpoints

2. **Require authentication for comparison endpoint** (04-05-02)
   - Uses `get_current_user` dependency (not optional)
   - Document comparison is compute-intensive (multiple documents, graph traversal)
   - Anonymous access could be added later with rate limiting

3. **Memory updated after each comparison interaction** (04-05-03)
   - Calls `summarizer.add_interaction()` with query and response
   - Enables memory summarization for long comparison sessions
   - Session ID tracked for multi-turn context

## Deviations from Plan

None - plan executed exactly as written.

## Success Criteria Met

| Criteria | Status | Evidence |
|----------|--------|----------|
| POST /api/v1/compare accepts document_ids and query | Pass | Endpoint at POST / with ComparisonRequest schema |
| Response includes similarities, differences, cross_document_insights | Pass | ComparisonResponse schema fields |
| Response includes citations with document sections | Pass | ComparisonCitation with document_id, chunk_id, filename, text |
| Session ID returned for multi-turn conversations | Pass | session_id in ComparisonResponse |
| Memory updated after each comparison interaction | Pass | summarizer.add_interaction() called |

## Commits

| Hash | Message |
|------|---------|
| 2cee804 | feat(04-05): add comparison request/response schemas |
| 010ea58 | feat(04-05): create document comparison API router |
| ea42857 | feat(04-05): register comparison router in main app |

## Phase 4 Complete

This plan completes Phase 4: LangGraph & Advanced Workflows.

**All 5 plans executed:**
- 04-01: PostgreSQL checkpointing + LangGraph infrastructure
- 04-02: GraphRAG multi-hop retrieval service
- 04-03: Document comparison LangGraph workflow
- 04-04: Memory summarization service
- 04-05: Document comparison API endpoint with citations

**Phase 4 Success Criteria Status:**
1. User can compare multiple documents - Pass (via POST /api/v1/compare)
2. System uses GraphRAG multi-hop reasoning - Pass (graphrag_service in workflow)
3. System automatically summarizes memory - Pass (memory_summarizer service)
4. LangGraph workflow state persists - Pass (PostgreSQL checkpointing)
5. Document comparison responses cite sources - Pass (ComparisonCitation)

## Next Phase Readiness

**Phase 5: Differentiation Features** is now unblocked.

Ready to implement:
- 05-01: On-demand document summarization service
- 05-02: Text simplification service with reading level control
- 05-03: Confidence scores and highlighted citations
- 05-04: Memory API and shared knowledge integration
