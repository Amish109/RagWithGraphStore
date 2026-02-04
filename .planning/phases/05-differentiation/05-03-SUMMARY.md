---
phase: 05-differentiation
plan: 03
subsystem: api
tags: [confidence-scoring, citations, logprobs, numpy, openai]

# Dependency graph
requires:
  - phase: 01-foundation-core-rag
    provides: generation_service, retrieval_service, schemas base
  - phase: 03-ux-streaming
    provides: queries API router, QueryResponse schema
provides:
  - Confidence scoring service via OpenAI logprobs
  - Highlighted citation extraction with exact text passages
  - Enhanced query endpoint with confidence and citations
affects: [06-production-hardening, API consumers]

# Tech tracking
tech-stack:
  added: [numpy]
  patterns: [logprobs confidence calculation, verbatim citation verification]

key-files:
  created:
    - backend/app/services/confidence_service.py
  modified:
    - backend/app/services/retrieval_service.py
    - backend/app/models/schemas.py
    - backend/app/api/queries.py

key-decisions:
  - "Geometric mean for confidence (stable for sequence comparison)"
  - "Thresholds: >=0.85 high, >=0.60 medium, <0.60 low"
  - "Verbatim verification prevents citation hallucination"
  - "Fallback to 200-char truncation if exact match fails"

patterns-established:
  - "Logprobs confidence: Use geometric_mean = np.exp(np.mean(log_probs))"
  - "Citation verification: Always string-search highlighted_passage in chunk_text"
  - "New endpoint for Phase 5 features: /enhanced alongside /query"

# Metrics
duration: 4min
completed: 2026-02-04
---

# Phase 5 Plan 03: Confidence Scores and Highlighted Citations Summary

**Confidence scoring via OpenAI logprobs with highlighted citations verifying exact text passages from source documents**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-04T15:08:17Z
- **Completed:** 2026-02-04T15:12:00Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- Confidence service calculates model certainty from logprobs (high/medium/low thresholds)
- Citation extraction identifies exact text passages supporting answers (verbatim verification)
- POST /enhanced endpoint returns QueryResponseWithCitations with confidence and highlighted citations
- Existing /query endpoint unchanged for backward compatibility

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Confidence Service** - `07c4ea0` (feat)
2. **Task 2: Add Enhanced Citation Extraction** - `01ec9ea` (feat)
3. **Task 3: Add Enhanced Query Endpoint** - `170e34e` (feat)

## Files Created/Modified
- `backend/app/services/confidence_service.py` - Confidence calculation from OpenAI logprobs
- `backend/app/services/retrieval_service.py` - Added extract_highlighted_citations function
- `backend/app/models/schemas.py` - ConfidenceScore, HighlightedCitation, QueryResponseWithCitations
- `backend/app/api/queries.py` - POST /enhanced endpoint

## Decisions Made
- **Geometric mean for confidence:** More stable than joint probability for sequence comparison (np.exp(np.mean(log_probs)))
- **Confidence thresholds:** >=0.85 high, >=0.60 medium, <0.60 low based on research recommendations
- **Empty logprobs handling:** Return score=0.5, level="unknown" to avoid errors
- **Citation verification:** Always verify highlighted_passage exists in chunk_text via string search
- **Fallback strategy:** Use first 200 chars of chunk if exact match fails (prevents hallucination)
- **Separate endpoint:** /enhanced for Phase 5 features preserves /query backward compatibility

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None - all syntax validation passed, confidence threshold tests verified.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Confidence scoring and highlighted citations ready for production use
- Memory API (05-04) can integrate confidence scores into memory-augmented queries
- Phase 6 load testing should include /enhanced endpoint

---
*Phase: 05-differentiation*
*Completed: 2026-02-04*
