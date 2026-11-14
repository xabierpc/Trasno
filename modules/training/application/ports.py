"""Ports de training: lo que los casos de uso necesitan de la persistencia.

El repositorio se construye ya ligado a un `user_id`, así que los casos de uso no lo manejan.
"""

from __future__ import annotations

from datetime import date
from typing import Protocol

from modules.training.domain.sesiones import Sesion


class RepositorioSesiones(Protocol):
    """Sesiones del usuario, cada una con sus ejercicios y series."""

    def guardar(self, sesion: Sesion) -> None:
        """Inserta la sesión completa (ejercicios y series incluidos)."""
        ...

    def listar(self, desde: date, hasta: date) -> list[Sesion]:
        """Sesiones con logical_date en [desde, hasta], ordenadas por fecha y timestamp."""
        ...

    def borrar(self, sesion_id: str) -> bool:
        """Borra la sesión con todo su contenido; devuelve False si no existía."""
        ...
