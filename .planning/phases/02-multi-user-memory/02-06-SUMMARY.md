---
phase: 02-multi-user-memory
plan: 06
subsystem: cleanup-and-shared-memory
tags: [ttl, cleanup, scheduler, admin, shared-memory, apscheduler]

dependency-graph:
  requires: ["02-03", "02-04"]
  provides: ["ttl-cleanup", "shared-memory-management", "admin-api"]
  affects: ["02-07"]

tech-stack:
  added: ["apscheduler>=3.10.0"]
  patterns: ["cron-scheduling", "sentinel-user-id", "prefix-filtering"]

key-files:
  created:
    - backend/app/jobs/__init__.py
    - backend/app/jobs/cleanup.py
    - backend/app/api/admin.py
  modified:
    - backend/pyproject.toml
    - backend/app/config.py
    - backend/app/services/memory_service.py
    - backend/app/main.py

decisions:
  - key: scheduler-library
    choice: "APScheduler"
    reason: "Lightweight, integrates with asyncio, supports cron expressions"
  - key: cleanup-timing
    choice: "Daily at 3 AM (configurable)"
    reason: "Off-peak hours, single daily run sufficient for TTL cleanup"
  - key: prefix-filtering
    choice: "STARTS WITH for Neo4j, Python filter for Qdrant"
    reason: "Qdrant lacks prefix match; post-filter after scroll is acceptable"
  - key: shared-memory-sentinel
    choice: "__shared__ user_id"
    reason: "Sentinel value clearly distinguishes shared from user memories"

metrics:
  duration: "5 min"
  completed: "2026-02-04"
---

# Phase 02 Plan 06: TTL Cleanup Scheduler + Shared Memory Management Summary

**One-liner:** APScheduler-based daily cleanup deletes expired anonymous data; admin endpoints manage company-wide shared memory accessible to all authenticated users.

## What Was Built

### Cleanup Scheduler (jobs/cleanup.py)
- `cleanup_expired_anonymous_data()` - Async function to delete expired data
- `setup_cleanup_scheduler()` - Initialize APScheduler with cron job
- `shutdown_cleanup_scheduler()` - Graceful shutdown
- Cleans Neo4j (documents, chunks) and Qdrant (vectors) for anonymous users
- Runs daily at configurable hour (default: 3 AM)

### Configuration (config.py)
- `ANONYMOUS_DATA_TTL_DAYS` - Days to keep anonymous data (default: 7)
- `CLEANUP_SCHEDULE_HOUR` - Hour to run cleanup (default: 3)

### Admin API (admin.py)
- `POST /admin/memory/shared` - Add fact to company-wide memory
- `GET /admin/memory/shared` - List all shared memories
- `DELETE /admin/memory/shared/{id}` - Delete shared memory
- All endpoints require admin role via `Depends(require_admin)`

### Memory Service Extensions (memory_service.py)
- `get_shared_memories(limit)` - List shared memories for admin
- `delete_shared_memory(memory_id)` - Delete shared memory
- Updated `search_with_shared` to mark personal memories with `is_shared=False`
- Return up to 2x limit when including shared results

### Main App Integration (main.py)
- Scheduler started in lifespan startup
- Scheduler shutdown in lifespan cleanup
- Admin router included with `/api/v1` prefix

## Technical Approach

### TTL Cleanup Strategy
1. Calculate cutoff datetime (now - TTL days)
2. Neo4j: DELETE where user_id STARTS WITH 'anon_' AND upload_date < cutoff
3. Qdrant: Scroll with created_at < cutoff, filter anonymous in Python, delete

### Shared Memory Architecture
- Uses sentinel `__shared__` as user_id for company memories
- All authenticated users can READ (via search_with_shared)
- Only admin can WRITE (via require_admin dependency)
- Anonymous users excluded from shared memory access

## Commits

| Hash | Description |
|------|-------------|
| 67d1813 | Create scheduled cleanup job for expired anonymous data |
| 00b88a5 | Create admin endpoints for shared memory management |

## Files Changed

| File | Change |
|------|--------|
| backend/pyproject.toml | Added apscheduler dependency |
| backend/app/config.py | Added TTL and schedule settings |
| backend/app/jobs/__init__.py | Created - module init |
| backend/app/jobs/cleanup.py | Created - cleanup scheduler |
| backend/app/services/memory_service.py | Added shared memory functions |
| backend/app/api/admin.py | Created - admin endpoints |
| backend/app/main.py | Integrated scheduler and admin router |

## Verification

```bash
# Verify scheduler module
cd backend && python -c "
import ast
with open('app/jobs/cleanup.py') as f:
    ast.parse(f.read())
print('Cleanup module OK')
"

# Verify admin routes
cd backend && python -c "
import ast
with open('app/api/admin.py') as f:
    ast.parse(f.read())
print('Admin API OK')
"

# Integration tests:
# 1. Create admin user: SET u.role='admin' in Neo4j
# 2. POST /admin/memory/shared with admin token
# 3. Search memories as regular user - should see shared
# 4. Search memories as anonymous - should NOT see shared
```

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

- TTL cleanup prevents unbounded growth of anonymous data
- Shared memory enables company-wide knowledge base
- Admin API provides memory management capabilities
- Ready for Plan 02-07 to verify multi-tenant isolation including shared memory boundaries
