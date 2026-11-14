"""Ports del briefing."""

from __future__ import annotations

from typing import Protocol


class Notificador(Protocol):
    """Avisa al usuario fuera de la aplicación (notificación de escritorio, Telegram…)."""

    def notificar(self, titulo: str, texto: str) -> None:
        """Muestra un aviso con `titulo` y `texto` en texto plano."""
        ...
