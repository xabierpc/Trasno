"""Modelos SQLAlchemy de `core.sqlite`: usuario, ajustes y log de acciones del agente."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, MetaData, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from core.db import TZDateTime

# Nombres de restricciones deterministas: necesarios para migraciones batch en SQLite.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base declarativa de las tablas del core."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class User(Base):
    """Usuario de Trasno (de momento hay uno solo, con id 1)."""

    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))


class Setting(Base):
    """Ajuste persistente de un usuario (clave → valor JSON)."""

    __tablename__ = "setting"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), primary_key=True
    )
    clave: Mapped[str] = mapped_column(String(100), primary_key=True)
    valor: Mapped[Any] = mapped_column(JSON)


class AgentLog(Base):
    """Registro de cada herramienta que el agente ejecuta o propone ejecutar."""

    __tablename__ = "agent_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True)
    herramienta: Mapped[str] = mapped_column(String(100))
    argumentos: Mapped[dict[str, Any]] = mapped_column(JSON)
    resultado: Mapped[str | None] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(TZDateTime, index=True)
    # propuesta | ejecutada | cancelada | fallida (core.contracts.EstadoAccion)
    estado: Mapped[str] = mapped_column(String(12), server_default="ejecutada")
