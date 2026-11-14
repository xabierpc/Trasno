"""Tablas iniciales de tracking: definiciones de métricas y entradas.

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
    op.create_table(
        "metric_definition",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("unidad", sa.String(length=30), nullable=False),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("agregacion", sa.String(length=20), nullable=False),
        sa.Column("on_duplicate", sa.String(length=20), nullable=False),
        sa.Column("objetivo", sa.Float(), nullable=True),
        sa.Column("minimo", sa.Float(), nullable=True),
        sa.Column("maximo", sa.Float(), nullable=True),
        sa.Column("escala_max", sa.Integer(), nullable=True),
        sa.Column("categorias", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "tipo IN ('numerica', 'duracion', 'booleana', 'escala', 'conteo', 'categorica')",
            name=op.f("ck_metric_definition_tipo"),
        ),
        sa.CheckConstraint(
            "agregacion IN ('suma', 'media', 'ultima')",
            name=op.f("ck_metric_definition_agregacion"),
        ),
        sa.CheckConstraint(
            "on_duplicate IN ('replace', 'keep_all')",
            name=op.f("ck_metric_definition_on_duplicate"),
        ),
        sa.CheckConstraint(
            "minimo IS NULL OR maximo IS NULL OR minimo <= maximo",
            name=op.f("ck_metric_definition_rango"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_metric_definition")),
        sa.UniqueConstraint("user_id", "nombre", name=op.f("uq_metric_definition_user_id")),
    )
    op.create_table(
        "metric_entry",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("metric_id", sa.String(length=36), nullable=False),
        sa.Column("valor_num", sa.Float(), nullable=True),
        sa.Column("valor_texto", sa.String(length=100), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("logical_date", sa.Date(), nullable=False),
        sa.Column("slot", sa.Integer(), nullable=False),
        sa.CheckConstraint("slot >= 0", name=op.f("ck_metric_entry_slot")),
        sa.CheckConstraint(
            "(valor_num IS NULL) <> (valor_texto IS NULL)", name=op.f("ck_metric_entry_un_valor")
        ),
        sa.ForeignKeyConstraint(
            ["metric_id"],
            ["metric_definition.id"],
            name=op.f("fk_metric_entry_metric_id_metric_definition"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_metric_entry")),
        sa.UniqueConstraint(
            "user_id", "metric_id", "logical_date", "slot", name=op.f("uq_metric_entry_user_id")
        ),
    )
    op.create_index(
        "ix_metric_entry_metric_id_logical_date", "metric_entry", ["metric_id", "logical_date"]
    )


def downgrade() -> None:
    op.drop_index("ix_metric_entry_metric_id_logical_date", table_name="metric_entry")
    op.drop_table("metric_entry")
    op.drop_table("metric_definition")
