"""Modelos SQLAlchemy de `planning.sqlite`: tareas, eventos y bloques recurrentes.

`user_id` no lleva FK porque `user` vive en `core.sqlite`, otro fichero. Las tres tablas son
independientes entre sí: no hay cascadas.
"""

from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy import (
    CheckConstraint,
    Date,
    Index,
    Integer,
    MetaData,
    String,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from core.db import TZDateTime
from core.models import NAMING_CONVENTION


class Base(DeclarativeBase):
    """Base declarativa de las tablas de planning."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TareaRow(Base):
    """Fila de una tarea."""

    __tablename__ = "tarea"
    __table_args__ = (
        CheckConstraint("prioridad IN ('baja', 'media', 'alta')", name="prioridad"),
        CheckConstraint("estado IN ('pendiente', 'hecha')", name="estado"),
        CheckConstraint("(estado = 'hecha') = (hecha_en IS NOT NULL)", name="hecha_en"),
        CheckConstraint("estimacion_min IS NULL OR estimacion_min > 0", name="estimacion"),
        Index("ix_tarea_user_id_fecha", "user_id", "fecha"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer)
    titulo: Mapped[str] = mapped_column(String(200))
    fecha: Mapped[date | None] = mapped_column(Date)
    prioridad: Mapped[str] = mapped_column(String(10))
    estimacion_min: Mapped[int | None] = mapped_column(Integer)
    estado: Mapped[str] = mapped_column(String(10))
    creada_en: Mapped[datetime] = mapped_column(TZDateTime)
    hecha_en: Mapped[datetime | None] = mapped_column(TZDateTime)


class EventoRow(Base):
    """Fila de un evento puntual. Los importados de un .ics no se repiten por usuario y UID."""

    __tablename__ = "evento"
    __table_args__ = (
        CheckConstraint("fin > inicio", name="intervalo"),
        CheckConstraint("origen IN ('manual', 'ics')", name="origen"),
        CheckConstraint("origen = 'manual' OR uid_externo IS NOT NULL", name="uid_ics"),
        UniqueConstraint("user_id", "uid_externo"),
        Index("ix_evento_user_id_inicio", "user_id", "inicio"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer)
    titulo: Mapped[str] = mapped_column(String(200))
    inicio: Mapped[datetime] = mapped_column(TZDateTime)
    fin: Mapped[datetime] = mapped_column(TZDateTime)
    lugar: Mapped[str | None] = mapped_column(String(200))
    origen: Mapped[str] = mapped_column(String(10))
    uid_externo: Mapped[str | None] = mapped_column(String(255))


class BloqueRow(Base):
    """Fila de un bloque recurrente semanal (horas en hora local)."""

    __tablename__ = "bloque"
    __table_args__ = (
        CheckConstraint("dia_semana BETWEEN 0 AND 6", name="dia_semana"),
        CheckConstraint("hora_fin > hora_inicio", name="horas"),
        CheckConstraint("desde IS NULL OR hasta IS NULL OR hasta >= desde", name="periodo"),
        Index("ix_bloque_user_id_dia_semana", "user_id", "dia_semana"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer)
    titulo: Mapped[str] = mapped_column(String(200))
    dia_semana: Mapped[int] = mapped_column(Integer)
    hora_inicio: Mapped[time] = mapped_column(Time)
    hora_fin: Mapped[time] = mapped_column(Time)
    desde: Mapped[date | None] = mapped_column(Date)
    hasta: Mapped[date | None] = mapped_column(Date)
    lugar: Mapped[str | None] = mapped_column(String(200))
