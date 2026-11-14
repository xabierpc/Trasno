"""Estado de las acciones del agente (propuesta, ejecutada, cancelada, fallida).

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
    # add_column directo, sin batch (ver docs/decisiones.md): las filas que ya existían eran
    # acciones ejecutadas, así que toman ese valor por defecto.
    op.add_column(
        "agent_log",
        sa.Column("estado", sa.String(length=12), server_default="ejecutada", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("agent_log", "estado")
