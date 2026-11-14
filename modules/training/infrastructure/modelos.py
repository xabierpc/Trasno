"""Modelos SQLAlchemy de `training.sqlite`: sesión → ejercicio → serie.

Borrar una sesión borra sus ejercicios y series (FK con ON DELETE CASCADE). `user_id` no
lleva FK porque `user` vive en `core.sqlite`, otro fichero.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    Float,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from core.db import TZDateTime
from core.models import NAMING_CONVENTION


class Base(DeclarativeBase):
    """Base declarativa de las tablas de training."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class SesionRow(Base):
    """Fila de una sesión de entreno."""

    __tablename__ = "sesion"
    __table_args__ = (
        CheckConstraint("duracion_min IS NULL OR duracion_min > 0", name="duracion"),
        CheckConstraint(
            "energia_previa IS NULL OR energia_previa BETWEEN 1 AND 10", name="energia"
        ),
        Index("ix_sesion_user_id_logical_date", "user_id", "logical_date"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer)
    logical_date: Mapped[date] = mapped_column(Date)
    tipo: Mapped[str] = mapped_column(String(50))
    duracion_min: Mapped[int | None] = mapped_column(Integer)
    energia_previa: Mapped[int | None] = mapped_column(Integer)
    timestamp: Mapped[datetime] = mapped_column(TZDateTime)

    ejercicios: Mapped[list[EjercicioRow]] = relationship(
        order_by="EjercicioRow.orden", cascade="all, delete-orphan", passive_deletes=True
    )


class EjercicioRow(Base):
    """Fila de un ejercicio dentro de una sesión; `orden` conserva el orden en que se hizo."""

    __tablename__ = "ejercicio"
    __table_args__ = (
        UniqueConstraint("sesion_id", "orden"),
        Index("ix_ejercicio_user_id_nombre", "user_id", "nombre"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer)
    sesion_id: Mapped[str] = mapped_column(ForeignKey("sesion.id", ondelete="CASCADE"))
    orden: Mapped[int] = mapped_column(Integer)
    nombre: Mapped[str] = mapped_column(String(100))

    series: Mapped[list[SerieRow]] = relationship(
        order_by="SerieRow.orden", cascade="all, delete-orphan", passive_deletes=True
    )


class SerieRow(Base):
    """Fila de una serie de un ejercicio."""

    __tablename__ = "serie"
    __table_args__ = (
        UniqueConstraint("ejercicio_id", "orden"),
        CheckConstraint("reps > 0", name="reps"),
        CheckConstraint("peso >= 0", name="peso"),
        CheckConstraint("rpe IS NULL OR rpe BETWEEN 1 AND 10", name="rpe"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer)
    ejercicio_id: Mapped[str] = mapped_column(ForeignKey("ejercicio.id", ondelete="CASCADE"))
    orden: Mapped[int] = mapped_column(Integer)
    reps: Mapped[int] = mapped_column(Integer)
    peso: Mapped[float] = mapped_column(Float)
    rpe: Mapped[float | None] = mapped_column(Float)
