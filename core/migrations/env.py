"""Entorno de Alembic para core.sqlite."""

from __future__ import annotations

from core.migraciones import ejecutar_env
from core.models import Base

ejecutar_env(Base.metadata, "core")
