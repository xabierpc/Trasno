"""Eventos de dominio que publica training en el bus."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from core.contracts import Event


@dataclass(frozen=True, kw_only=True)
class SesionRegistrada(Event):
    """Se ha guardado una sesión de entreno."""

    sesion_id: str
    logical_date: date
    tipo: str
    volumen: float


@dataclass(frozen=True, kw_only=True)
class SesionBorrada(Event):
    """Se ha borrado una sesión: quien guarde una referencia a ella debe limpiarla."""

    sesion_id: str
