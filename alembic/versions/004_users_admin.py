"""Add is_admin and is_active flags on users.

Revision ID: 004_users_admin
Revises: 003_users_auth
Create Date: 2026-07-14
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_users_admin"
down_revision: Union[str, None] = "003_users_auth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
    )
    # Promote seeded admin email if present
    op.execute(
        "UPDATE users SET is_admin = true WHERE email = 'admin@lexai.com'"
    )


def downgrade() -> None:
    op.drop_column("users", "is_active")
    op.drop_column("users", "is_admin")
