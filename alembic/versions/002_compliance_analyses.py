"""Add compliance_analyses history table.

Revision ID: 002_compliance_analyses
Revises: 001_initial
Create Date: 2026-07-14

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_compliance_analyses"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "compliance_analyses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("jurisdiction", sa.String(length=128), nullable=False),
        sa.Column("compliance_score", sa.Integer(), nullable=False),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_compliance_analyses_jurisdiction", "compliance_analyses", ["jurisdiction"])
    op.create_index("ix_compliance_analyses_risk_level", "compliance_analyses", ["risk_level"])
    op.create_index("ix_compliance_analyses_created_at", "compliance_analyses", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_compliance_analyses_created_at", table_name="compliance_analyses")
    op.drop_index("ix_compliance_analyses_risk_level", table_name="compliance_analyses")
    op.drop_index("ix_compliance_analyses_jurisdiction", table_name="compliance_analyses")
    op.drop_table("compliance_analyses")
