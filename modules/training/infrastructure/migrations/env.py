"""Entorno de Alembic para training.sqlite."""

from __future__ import annotations

from core.migraciones import ejecutar_env
from modules.training.infrastructure.modelos import Base

ejecutar_env(Base.metadata, "training")
