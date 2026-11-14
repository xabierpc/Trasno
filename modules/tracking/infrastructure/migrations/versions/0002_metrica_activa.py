"""Añade `activa` a las definiciones de métricas.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-14
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ALTER TABLE directo, sin batch: el modo batch recrea la tabla y, con foreign_keys=ON,
    # borrar la antigua arrastraría en cascada todas las entradas de metric_entry.
    op.add_column(
        "metric_definition",
        sa.Column("activa", sa.Boolean(), server_default=sa.true(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("metric_definition", "activa")
