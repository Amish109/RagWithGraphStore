---
phase: 02-multi-user-memory
plan: 03
subsystem: security
tags: [rbac, authorization, jwt, roles, fastapi]
dependency-graph:
  requires:
    - 01-02 (JWT authentication foundation)
    - 02-01 (refresh token rotation)
  provides:
    - Role enum (USER, ADMIN, ANONYMOUS)
    - RoleChecker dependency for FastAPI
    - require_admin, require_user convenience dependencies
    - Role in JWT tokens for fast authorization
  affects:
    - 02-04 (memory API uses require_admin for shared memory)
    - 02-06 (admin-only cleanup operations)
tech-stack:
  added: []
  patterns:
    - FastAPI dependency injection for role checking
    - Role enum with str inheritance for JSON serialization
    - JWT payload includes role for stateless authorization
key-files:
  created:
    - backend/app/core/rbac.py
  modified:
    - backend/app/models/user.py
    - backend/app/core/auth.py
    - backend/app/core/security.py
    - backend/app/api/auth.py
decisions:
  - decision: "Role stored in JWT for fast authorization"
    rationale: "Avoids database lookup on every request"
    tradeoff: "Role changes require token refresh to take effect"
  - decision: "Default role is 'user', admin assigned manually"
    rationale: "Prevents privilege escalation via registration"
    tradeoff: "Admin creation requires database access"
  - decision: "RoleChecker uses get_current_user, not optional variant"
    rationale: "Role-protected endpoints require authentication"
    tradeoff: "Anonymous endpoints must use different dependency"
metrics:
  duration: 3 min
  completed: 2026-02-04
---

# Phase 2 Plan 03: RBAC with User/Admin Roles Summary

**One-liner:** Role-based access control via FastAPI dependencies with JWT-embedded roles.

## What Was Built

Implemented role-based access control (RBAC) with user and admin roles using FastAPI's dependency injection system. The Role enum defines three values: USER, ADMIN, and ANONYMOUS. RoleChecker is a callable class that validates user roles against allowed roles, returning 403 Forbidden if the user lacks permission.

Convenience dependencies `require_admin` and `require_user` provide common access patterns. Admin-only endpoints use `Depends(require_admin)`, while authenticated endpoints use `Depends(require_user)` which allows both user and admin roles.

Roles are stored in the User node in Neo4j and included in JWT tokens for fast authorization without database lookup on every request.

## Key Technical Details

### Role Enum
```python
class Role(str, Enum):
    USER = "user"
    ADMIN = "admin"
    ANONYMOUS = "anonymous"
```

### RoleChecker Dependency
```python
@router.post("/admin-only")
async def admin_endpoint(user: UserContext = Depends(require_admin)):
    # Only admins can access
    ...
```

### JWT Token with Role
```python
{
    "sub": "user@example.com",
    "user_id": "uuid-123",
    "role": "admin",  # <-- role included
    "jti": "token-id",
    "exp": 1770123456
}
```

### User Model Update
- `create_user()` now accepts optional `role` parameter (default: "user")
- Neo4j User node includes `role` property

## Deviations from Plan

None - plan executed exactly as written.

## Files Changed

| File | Change |
|------|--------|
| backend/app/core/rbac.py | Created - Role enum, RoleChecker, convenience dependencies |
| backend/app/models/user.py | Modified - Added role parameter to create_user |
| backend/app/core/auth.py | Modified - Added role to create_token_pair |
| backend/app/core/security.py | Modified - Extract role from token in get_current_user |
| backend/app/api/auth.py | Modified - Pass user role to create_token_pair on login/refresh |

## Verification Results

All verification commands passed:
- Role enum has USER, ADMIN, ANONYMOUS values
- create_user accepts role parameter
- JWT tokens include role in payload
- Role preserved during token refresh

## Next Phase Readiness

Plan 02-04 (Memory Service) can use `require_admin` for shared memory endpoint.
Plan 02-06 (TTL Cleanup) can use `require_admin` for admin-only cleanup operations.
