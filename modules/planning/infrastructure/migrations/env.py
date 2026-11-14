"""Entorno de Alembic para planning.sqlite."""

from __future__ import annotations

from core.migraciones import ejecutar_env
from modules.planning.infrastructure.modelos import Base

ejecutar_env(Base.metadata, "planning")
