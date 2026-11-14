"""Modelos SQLAlchemy de `tracking.sqlite`: definiciones de métricas y sus entradas.

El valor de una entrada va en `valor_num` (numérica, duración, escala, conteo y booleana
como 0/1) o en `valor_texto` (categórica); un CHECK garantiza que se usa exactamente una.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    JSON,
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
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from core.db import TZDateTime
from core.models import NAMING_CONVENTION
from modules.tracking.domain.metricas import Agregacion, PoliticaDuplicado, TipoMetrica


def _en(columna: str, valores: type[TipoMetrica | Agregacion | PoliticaDuplicado]) -> str:
    """Expresión CHECK `columna IN (...)` con los valores de un enum del dominio."""
    return f"{columna} IN ({', '.join(repr(v.value) for v in valores)})"


class Base(DeclarativeBase):
    """Base declarativa de las tablas de tracking."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class MetricDefinitionRow(Base):
    """Fila de una definición de métrica; el nombre es único por usuario."""

    __tablename__ = "metric_definition"
    __table_args__ = (
        UniqueConstraint("user_id", "nombre"),
        CheckConstraint(_en("tipo", TipoMetrica), name="tipo"),
        CheckConstraint(_en("agregacion", Agregacion), name="agregacion"),
        CheckConstraint(_en("on_duplicate", PoliticaDuplicado), name="on_duplicate"),
        CheckConstraint("minimo IS NULL OR maximo IS NULL OR minimo <= maximo", name="rango"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer)
    nombre: Mapped[str] = mapped_column(String(100))
    unidad: Mapped[str] = mapped_column(String(30))
    tipo: Mapped[str] = mapped_column(String(20))
    agregacion: Mapped[str] = mapped_column(String(20))
    on_duplicate: Mapped[str] = mapped_column(String(20))
    objetivo: Mapped[float | None] = mapped_column(Float)
    minimo: Mapped[float | None] = mapped_column(Float)
    maximo: Mapped[float | None] = mapped_column(Float)
    escala_max: Mapped[int | None] = mapped_column(Integer)
    categorias: Mapped[list[str]] = mapped_column(JSON)


class MetricEntryRow(Base):
    """Fila de una entrada; (user_id, metric_id, logical_date, slot) es único."""

    __tablename__ = "metric_entry"
    __table_args__ = (
        UniqueConstraint("user_id", "metric_id", "logical_date", "slot"),
        CheckConstraint("slot >= 0", name="slot"),
        CheckConstraint("(valor_num IS NULL) <> (valor_texto IS NULL)", name="un_valor"),
        Index("ix_metric_entry_metric_id_logical_date", "metric_id", "logical_date"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer)
    metric_id: Mapped[str] = mapped_column(ForeignKey("metric_definition.id", ondelete="CASCADE"))
    valor_num: Mapped[float | None] = mapped_column(Float)
    valor_texto: Mapped[str | None] = mapped_column(String(100))
    timestamp: Mapped[datetime] = mapped_column(TZDateTime)
    logical_date: Mapped[date] = mapped_column(Date)
    slot: Mapped[int] = mapped_column(Integer, default=0)
