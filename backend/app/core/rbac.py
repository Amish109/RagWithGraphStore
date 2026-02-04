"""Role-Based Access Control (RBAC) for FastAPI endpoints.

Implements role checking via FastAPI dependency injection:
- Role enum defines USER, ADMIN, ANONYMOUS roles
- RoleChecker dependency validates user role against allowed roles
- Convenience dependencies for common access patterns

Following research Pattern 6 for RBAC implementation.

Usage:
    @router.post("/admin-only")
    async def admin_endpoint(user: UserContext = Depends(require_admin)):
        ...

    @router.post("/authenticated-only")
    async def auth_endpoint(user: UserContext = Depends(require_user)):
        ...
"""

from enum import Enum

from fastapi import Depends, HTTPException, status

from app.core.security import get_current_user
from app.models.schemas import UserContext


class Role(str, Enum):
    """User roles for access control.

    Values:
        USER: Default role for registered users
        ADMIN: Administrative access for shared memory management
        ANONYMOUS: Implicit role for unauthenticated sessions
    """

    USER = "user"
    ADMIN = "admin"
    ANONYMOUS = "anonymous"


class RoleChecker:
    """Dependency for role-based access control.

    Validates that the authenticated user has one of the allowed roles.
    Returns the UserContext if authorized, raises 403 Forbidden otherwise.

    Note: RoleChecker uses get_current_user (not optional), so it requires
    authentication. Anonymous endpoints should not use RoleChecker - they
    should use get_current_user_optional instead.

    Attributes:
        allowed_roles: List of Role values that are permitted to access the endpoint.
    """

    def __init__(self, allowed_roles: list[Role]):
        """Initialize RoleChecker with allowed roles.

        Args:
            allowed_roles: List of Role values that are permitted.
        """
        self.allowed_roles = allowed_roles

    async def __call__(self, user: dict = Depends(get_current_user)) -> UserContext:
        """Check if user has required role.

        Args:
            user: User dict from get_current_user dependency.

        Returns:
            UserContext for the authenticated user.

        Raises:
            HTTPException 403: If user role not in allowed_roles.
        """
        # Get user's role, default to USER if not set
        user_role_str = user.get("role", "user")

        # Convert to Role enum, default to USER for unknown roles
        try:
            user_role = Role(user_role_str)
        except ValueError:
            user_role = Role.USER

        if user_role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {[r.value for r in self.allowed_roles]}",
            )

        # Return UserContext for consistency with get_current_user_optional
        return UserContext(
            id=user["id"],
            email=user.get("email"),
            is_anonymous=False,
            role=user_role_str,
            jti=user.get("jti"),
        )


# Convenience dependencies for common access patterns
require_admin = RoleChecker([Role.ADMIN])
"""Dependency that requires admin role. Use for admin-only endpoints."""

require_user = RoleChecker([Role.USER, Role.ADMIN])
"""Dependency that allows both user and admin roles. Admin can do user things."""

require_authenticated = RoleChecker([Role.USER, Role.ADMIN])
"""Alias for require_user. Requires any authenticated user."""
