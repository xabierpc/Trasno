"""Entorno de Alembic para tracking.sqlite."""

from __future__ import annotations

from core.migraciones import ejecutar_env
from modules.tracking.infrastructure.modelos import Base

ejecutar_env(Base.metadata, "tracking")
