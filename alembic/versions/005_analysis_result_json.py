"""Store full analyze payload on compliance_analyses for History → Results.

Revision ID: 005_analysis_result_json
Revises: 004_users_admin
Create Date: 2026-07-14
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_analysis_result_json"
down_revision: Union[str, None] = "004_users_admin"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "compliance_analyses",
        sa.Column("result_json", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("compliance_analyses", "result_json")
