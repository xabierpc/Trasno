"""Tablas iniciales de training: sesión, ejercicio y serie.

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
        "sesion",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("logical_date", sa.Date(), nullable=False),
        sa.Column("tipo", sa.String(length=50), nullable=False),
        sa.Column("duracion_min", sa.Integer(), nullable=True),
        sa.Column("energia_previa", sa.Integer(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "duracion_min IS NULL OR duracion_min > 0", name=op.f("ck_sesion_duracion")
        ),
        sa.CheckConstraint(
            "energia_previa IS NULL OR energia_previa BETWEEN 1 AND 10",
            name=op.f("ck_sesion_energia"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sesion")),
    )
    op.create_index("ix_sesion_user_id_logical_date", "sesion", ["user_id", "logical_date"])
    op.create_table(
        "ejercicio",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("sesion_id", sa.String(length=36), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(
            ["sesion_id"],
            ["sesion.id"],
            name=op.f("fk_ejercicio_sesion_id_sesion"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ejercicio")),
        sa.UniqueConstraint("sesion_id", "orden", name=op.f("uq_ejercicio_sesion_id")),
    )
    op.create_index("ix_ejercicio_user_id_nombre", "ejercicio", ["user_id", "nombre"])
    op.create_table(
        "serie",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("ejercicio_id", sa.String(length=36), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("reps", sa.Integer(), nullable=False),
        sa.Column("peso", sa.Float(), nullable=False),
        sa.Column("rpe", sa.Float(), nullable=True),
        sa.CheckConstraint("reps > 0", name=op.f("ck_serie_reps")),
        sa.CheckConstraint("peso >= 0", name=op.f("ck_serie_peso")),
        sa.CheckConstraint("rpe IS NULL OR rpe BETWEEN 1 AND 10", name=op.f("ck_serie_rpe")),
        sa.ForeignKeyConstraint(
            ["ejercicio_id"],
            ["ejercicio.id"],
            name=op.f("fk_serie_ejercicio_id_ejercicio"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_serie")),
        sa.UniqueConstraint("ejercicio_id", "orden", name=op.f("uq_serie_ejercicio_id")),
    )


def downgrade() -> None:
    op.drop_table("serie")
    op.drop_index("ix_ejercicio_user_id_nombre", table_name="ejercicio")
    op.drop_table("ejercicio")
    op.drop_index("ix_sesion_user_id_logical_date", table_name="sesion")
    op.drop_table("sesion")
