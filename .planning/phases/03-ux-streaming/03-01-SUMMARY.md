---
phase: 03-ux-streaming
plan: 01
subsystem: api
tags: [fastapi, error-handling, pydantic, exception-handlers]

# Dependency graph
requires:
  - phase: 02-multi-user-memory
    provides: FastAPI app structure with routers and middleware
provides:
  - Global exception handlers for consistent error responses
  - ErrorResponse schema for standardized API errors
  - Domain exceptions for documents and queries
affects: [03-02, 03-03, 03-04, 04-01, 04-02, 04-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Global exception handlers via register_exception_handlers()
    - ErrorResponse schema for all API errors
    - Domain-specific HTTPException subclasses

key-files:
  created:
    - backend/app/core/error_handlers.py
  modified:
    - backend/app/core/exceptions.py
    - backend/app/models/schemas.py
    - backend/app/main.py

key-decisions:
  - "Status code to error type mapping for consistent error strings"
  - "Skip 'body' prefix in validation error field paths for cleaner messages"
  - "Generic exception handler logs full details but returns sanitized message"

patterns-established:
  - "ErrorResponse(error, message, detail) schema for all API errors"
  - "Domain exceptions extend HTTPException with specific status codes"
  - "register_exception_handlers(app) called before CORS middleware"

# Metrics
duration: 4min
completed: 2026-02-04
---

# Phase 3 Plan 01: Global Exception Handlers Summary

**Global exception handlers with ErrorResponse schema for consistent, user-friendly API error responses without exposing internal details**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-04T20:00:00Z
- **Completed:** 2026-02-04T20:04:00Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- ErrorResponse schema with error type, message, and optional detail fields
- Domain exceptions for DocumentNotFoundError, DocumentProcessingError, QueryGenerationError
- Global exception handlers for validation errors (422), HTTP exceptions, and unhandled errors (500)
- Exception handlers registered in main.py for all API endpoints

## Task Commits

Each task was committed atomically:

1. **Task 1: Add ErrorResponse schema and domain exceptions** - `e60ead9` (feat)
2. **Task 2: Create global exception handlers** - `961fe8f` (feat)
3. **Task 3: Register handlers in main.py** - `494294c` (feat)

## Files Created/Modified
- `backend/app/core/error_handlers.py` - Global exception handlers with register function
- `backend/app/core/exceptions.py` - Domain exceptions for documents and queries
- `backend/app/models/schemas.py` - ErrorResponse schema for standardized errors
- `backend/app/main.py` - Import and registration of exception handlers

## Decisions Made
- Status code to error type mapping (400=bad_request, 401=unauthorized, etc.)
- Skip 'body' prefix in validation error field paths for cleaner user messages
- Log full exception details internally, return sanitized "unexpected error" message externally

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Error handling foundation complete for streaming endpoints
- All API errors now return consistent ErrorResponse format
- Ready for SSE streaming implementation in Plan 03-03

---
*Phase: 03-ux-streaming*
*Completed: 2026-02-04*
