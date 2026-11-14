"""Tablas iniciales del core y usuario único.

Revision ID: 0001
Revises:
Create Date: 2026-11-14
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    user = op.create_table(
        "user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user")),
    )
    op.create_table(
        "setting",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("clave", sa.String(length=100), nullable=False),
        sa.Column("valor", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user.id"], name=op.f("fk_setting_user_id_user"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("user_id", "clave", name=op.f("pk_setting")),
    )
    op.create_table(
        "agent_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("herramienta", sa.String(length=100), nullable=False),
        sa.Column("argumentos", sa.JSON(), nullable=False),
        sa.Column("resultado", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user.id"], name=op.f("fk_agent_log_user_id_user"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_agent_log")),
    )
    op.create_index(op.f("ix_agent_log_user_id"), "agent_log", ["user_id"])
    op.create_index(op.f("ix_agent_log_timestamp"), "agent_log", ["timestamp"])

    # Trasno tiene un único usuario; su id coincide con Settings.user_id por defecto.
    op.bulk_insert(user, [{"id": 1, "nombre": "usuario"}])


def downgrade() -> None:
    op.drop_index(op.f("ix_agent_log_timestamp"), table_name="agent_log")
    op.drop_index(op.f("ix_agent_log_user_id"), table_name="agent_log")
    op.drop_table("agent_log")
    op.drop_table("setting")
    op.drop_table("user")
