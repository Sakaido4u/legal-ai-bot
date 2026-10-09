#!/usr/bin/env python3
"""
Create (or update) a user who can log in to the /demo pages.

Uses the same PBKDF2 password hashing as the API (backend.auth.hash_password)
and the DATABASE_URL from .env. Run from the repo root so .env is found.

Usage (PowerShell):
  $env:PYTHONPATH="src"
  python scripts/create_demo_user.py --email researcher@example.com --name "Researcher"
  (you are then asked for the password; typing is hidden)

If the email already exists, its name and password are updated.
"""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sqlalchemy.exc import OperationalError, ProgrammingError  # noqa: E402

from backend.auth import hash_password  # noqa: E402
from database import crud  # noqa: E402
from database.session import SessionLocal  # noqa: E402

MIN_PASSWORD = 6  # same minimum as POST /auth/register


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Create or update a demo login user.")
    p.add_argument("--email", required=True, help="login email")
    p.add_argument("--name", default="Demo Researcher", help="display name shown on pages and PDFs")
    p.add_argument("--admin", action="store_true", help="give the user admin rights")
    return p.parse_args()


def ask_password() -> str:
    while True:
        first = getpass.getpass("Password (hidden): ")
        if len(first) < MIN_PASSWORD:
            print(f"Password must be at least {MIN_PASSWORD} characters.")
            continue
        if getpass.getpass("Repeat password: ") != first:
            print("Passwords did not match, try again.")
            continue
        return first


def main() -> None:
    args = parse_args()
    email = args.email.strip().lower()
    if "@" not in email:
        raise SystemExit("Please give a valid email address.")
    password = ask_password()

    db = SessionLocal()
    try:
        user = crud.get_user_by_email(db, email)
        if user is None:
            crud.create_user(
                db,
                email=email,
                name=args.name,
                hashed_password=hash_password(password),
                is_admin=args.admin,
            )
            action = "Created"
        else:
            user.name = args.name.strip()
            user.hashed_password = hash_password(password)
            user.is_active = True
            user.is_admin = user.is_admin or args.admin
            action = "Updated"
        db.commit()
    except OperationalError as exc:
        raise SystemExit(
            "Could not connect to PostgreSQL. Check DATABASE_URL in .env and that the "
            f"postgresql service is running.\nDetails: {exc.orig}"
        ) from exc
    except ProgrammingError as exc:
        raise SystemExit(
            "The users table is missing. Create the tables first with:  alembic upgrade head"
            f"\nDetails: {exc.orig}"
        ) from exc
    finally:
        db.close()

    print(f"{action} user {email} ({args.name}). Log in at http://127.0.0.1:8000/demo/login")


if __name__ == "__main__":
    main()
