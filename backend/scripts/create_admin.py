#!/usr/bin/env python
"""
Bootstrap script — Create the initial admin user.

Usage:
    python -m scripts.create_admin --username admin --email admin@ipam.local --password <password>

Or run directly:
    python scripts/create_admin.py --username admin --email admin@ipam.local --password <password>

This script connects directly to the database using SessionLocal
and creates a user with the 'admin' role. It is intended for
first-time setup when no admin exists yet.
"""

import argparse
import sys
import os

# Ensure the backend package is importable when run from the backend/ directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.services.auth_service import hash_password


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create an admin user for the IPAM application."
    )
    parser.add_argument("--username", required=True, help="Admin username")
    parser.add_argument("--email", required=True, help="Admin email address")
    parser.add_argument("--password", required=True, help="Admin password (min 8 chars)")
    args = parser.parse_args()

    if len(args.password) < 8:
        print("Error: Password must be at least 8 characters.", file=sys.stderr)
        sys.exit(1)

    db = SessionLocal()
    try:
        repo = UserRepository(db)

        # Check for existing user
        if repo.get_by_username(args.username):
            print(f"Error: Username '{args.username}' already exists.", file=sys.stderr)
            sys.exit(1)
        if repo.get_by_email(args.email):
            print(f"Error: Email '{args.email}' already exists.", file=sys.stderr)
            sys.exit(1)

        user = User(
            username=args.username,
            email=args.email,
            hashed_password=hash_password(args.password),
            role="admin",
        )
        repo.create(user)
        print(f"✓ Admin user '{args.username}' created successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
