#!/usr/bin/env python3
"""Create an admin user for testing.

Usage:
    cd backend
    python scripts/create_admin.py admin@example.com yourpassword
"""

import sys
import uuid
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.auth import hash_password
from app.models.user import create_user, get_user_by_email


def main():
    if len(sys.argv) != 3:
        print("Usage: python scripts/create_admin.py <email> <password>")
        print("Example: python scripts/create_admin.py admin@example.com secret123")
        sys.exit(1)

    email = sys.argv[1]
    password = sys.argv[2]

    # Check if user already exists
    existing = get_user_by_email(email)
    if existing:
        print(f"User {email} already exists with role: {existing.get('role', 'user')}")
        print("To promote to admin, run in Neo4j Browser:")
        print(f'  MATCH (u:User {{email: "{email}"}}) SET u.role = "admin" RETURN u')
        sys.exit(1)

    # Create admin user
    user_id = str(uuid.uuid4())
    hashed = hash_password(password)
    user = create_user(email, hashed, user_id, role="admin")

    print(f"Admin user created successfully!")
    print(f"  Email: {email}")
    print(f"  User ID: {user_id}")
    print(f"  Role: admin")
    print(f"\nYou can now login with these credentials in the frontend.")


if __name__ == "__main__":
    main()
