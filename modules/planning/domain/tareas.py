"""Tareas: algo que hacer, opcionalmente para un día lógico, con prioridad y estimación."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, replace
from datetime import date, datetime
from enum import StrEnum

from modules.planning.domain.errores import TareaInvalida


class Prioridad(StrEnum):
    """Prioridad de una tarea. Los valores se guardan en la BD: no cambiarlos."""

    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"


class EstadoTarea(StrEnum):
    """Estado de una tarea. Los valores se guardan en la BD: no cambiarlos."""

    PENDIENTE = "pendiente"
    HECHA = "hecha"


def _nuevo_id() -> str:
    return str(uuid.uuid4())


def _con_zona(instante: datetime) -> bool:
    return instante.tzinfo is not None and instante.utcoffset() is not None


@dataclass(frozen=True, kw_only=True)
class Tarea:
    """Una tarea. Sin `fecha` es una tarea sin día asignado (bandeja de entrada)."""

    titulo: str
    creada_en: datetime
    fecha: date | None = None
    prioridad: Prioridad = Prioridad.MEDIA
    estimacion_min: int | None = None
    estado: EstadoTarea = EstadoTarea.PENDIENTE
    hecha_en: datetime | None = None
    id: str = field(default_factory=_nuevo_id)

    def __post_init__(self) -> None:
        object.__setattr__(self, "titulo", " ".join(self.titulo.split()))
        if not self.titulo:
            raise TareaInvalida("El título de la tarea no puede estar vacío")
        if not _con_zona(self.creada_en):
            raise TareaInvalida("`creada_en` debe llevar zona horaria")
        if self.estimacion_min is not None and (
            not isinstance(self.estimacion_min, int)
            or isinstance(self.estimacion_min, bool)
            or self.estimacion_min <= 0
        ):
            raise TareaInvalida(f"La estimación debe ser > 0 minutos: {self.estimacion_min!r}")
        hecha = self.estado is EstadoTarea.HECHA
        if hecha != (self.hecha_en is not None):
            raise TareaInvalida("Una tarea hecha lleva `hecha_en` y una pendiente no")
        if self.hecha_en is not None and not _con_zona(self.hecha_en):
            raise TareaInvalida("`hecha_en` debe llevar zona horaria")

    @property
    def hecha(self) -> bool:
        return self.estado is EstadoTarea.HECHA

    def completar(self, ahora: datetime) -> Tarea:
        """Devuelve la tarea marcada como hecha. Completar una ya hecha no cambia nada."""
        if self.hecha:
            return self
        return replace(self, estado=EstadoTarea.HECHA, hecha_en=ahora)

    def reabrir(self) -> Tarea:
        """Devuelve la tarea otra vez pendiente."""
        return replace(self, estado=EstadoTarea.PENDIENTE, hecha_en=None)

    def mover(self, fecha: date | None) -> Tarea:
        """Devuelve la tarea asignada a otro día (o a ninguno)."""
        return replace(self, fecha=fecha)
