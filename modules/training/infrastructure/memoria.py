"""Repositorio en memoria de training: para tests y para probar sin base de datos."""

from __future__ import annotations

from datetime import date

from modules.training.domain.sesiones import Sesion


class RepositorioSesionesMemoria:
    """Implementa `RepositorioSesiones` sobre un diccionario."""

    def __init__(self) -> None:
        self._sesiones: dict[str, Sesion] = {}

    def guardar(self, sesion: Sesion) -> None:
        self._sesiones[sesion.id] = sesion

    def listar(self, desde: date, hasta: date) -> list[Sesion]:
        return sorted(
            (s for s in self._sesiones.values() if desde <= s.logical_date <= hasta),
            key=lambda s: (s.logical_date, s.timestamp),
        )

    def borrar(self, sesion_id: str) -> bool:
        return self._sesiones.pop(sesion_id, None) is not None
