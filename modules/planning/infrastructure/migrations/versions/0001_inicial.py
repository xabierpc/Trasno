"""Tablas iniciales de planning: tarea, evento y bloque.

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
        "tarea",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("titulo", sa.String(length=200), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=True),
        sa.Column("prioridad", sa.String(length=10), nullable=False),
        sa.Column("estimacion_min", sa.Integer(), nullable=True),
        sa.Column("estado", sa.String(length=10), nullable=False),
        sa.Column("creada_en", sa.DateTime(), nullable=False),
        sa.Column("hecha_en", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "prioridad IN ('baja', 'media', 'alta')", name=op.f("ck_tarea_prioridad")
        ),
        sa.CheckConstraint("estado IN ('pendiente', 'hecha')", name=op.f("ck_tarea_estado")),
        sa.CheckConstraint(
            "(estado = 'hecha') = (hecha_en IS NOT NULL)", name=op.f("ck_tarea_hecha_en")
        ),
        sa.CheckConstraint(
            "estimacion_min IS NULL OR estimacion_min > 0", name=op.f("ck_tarea_estimacion")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tarea")),
    )
    op.create_index("ix_tarea_user_id_fecha", "tarea", ["user_id", "fecha"])
    op.create_table(
        "evento",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("titulo", sa.String(length=200), nullable=False),
        sa.Column("inicio", sa.DateTime(), nullable=False),
        sa.Column("fin", sa.DateTime(), nullable=False),
        sa.Column("lugar", sa.String(length=200), nullable=True),
        sa.Column("origen", sa.String(length=10), nullable=False),
        sa.Column("uid_externo", sa.String(length=255), nullable=True),
        sa.CheckConstraint("fin > inicio", name=op.f("ck_evento_intervalo")),
        sa.CheckConstraint("origen IN ('manual', 'ics')", name=op.f("ck_evento_origen")),
        sa.CheckConstraint(
            "origen = 'manual' OR uid_externo IS NOT NULL", name=op.f("ck_evento_uid_ics")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evento")),
        sa.UniqueConstraint("user_id", "uid_externo", name=op.f("uq_evento_user_id")),
    )
    op.create_index("ix_evento_user_id_inicio", "evento", ["user_id", "inicio"])
    op.create_table(
        "bloque",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("titulo", sa.String(length=200), nullable=False),
        sa.Column("dia_semana", sa.Integer(), nullable=False),
        sa.Column("hora_inicio", sa.Time(), nullable=False),
        sa.Column("hora_fin", sa.Time(), nullable=False),
        sa.Column("desde", sa.Date(), nullable=True),
        sa.Column("hasta", sa.Date(), nullable=True),
        sa.Column("lugar", sa.String(length=200), nullable=True),
        sa.CheckConstraint("dia_semana BETWEEN 0 AND 6", name=op.f("ck_bloque_dia_semana")),
        sa.CheckConstraint("hora_fin > hora_inicio", name=op.f("ck_bloque_horas")),
        sa.CheckConstraint(
            "desde IS NULL OR hasta IS NULL OR hasta >= desde", name=op.f("ck_bloque_periodo")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bloque")),
    )
    op.create_index("ix_bloque_user_id_dia_semana", "bloque", ["user_id", "dia_semana"])


def downgrade() -> None:
    op.drop_index("ix_bloque_user_id_dia_semana", table_name="bloque")
    op.drop_table("bloque")
    op.drop_index("ix_evento_user_id_inicio", table_name="evento")
    op.drop_table("evento")
    op.drop_index("ix_tarea_user_id_fecha", table_name="tarea")
    op.drop_table("tarea")
