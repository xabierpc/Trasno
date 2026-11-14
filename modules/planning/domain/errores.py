"""Errores de dominio de planning."""

from __future__ import annotations


class ErrorPlanning(Exception):
    """Base de los errores de planning."""


class TareaInvalida(ErrorPlanning):
    """Una tarea es incoherente (título vacío, estimación <= 0...)."""


class EventoInvalido(ErrorPlanning):
    """Un evento es incoherente (título vacío, fin <= inicio, fechas sin zona...)."""


class BloqueInvalido(ErrorPlanning):
    """Un bloque recurrente es incoherente (día de la semana fuera de rango, fin <= inicio...)."""


class TareaNoEncontrada(ErrorPlanning):
    """No existe ninguna tarea con ese identificador."""

    def __init__(self, tarea_id: str) -> None:
        super().__init__(f"No existe la tarea {tarea_id!r}")
        self.tarea_id = tarea_id


class EventoNoEncontrado(ErrorPlanning):
    """No existe ningún evento con ese identificador."""

    def __init__(self, evento_id: str) -> None:
        super().__init__(f"No existe el evento {evento_id!r}")
        self.evento_id = evento_id


class BloqueNoEncontrado(ErrorPlanning):
    """No existe ningún bloque recurrente con ese identificador."""

    def __init__(self, bloque_id: str) -> None:
        super().__init__(f"No existe el bloque {bloque_id!r}")
        self.bloque_id = bloque_id


class CalendarioInvalido(ErrorPlanning):
    """El fichero no es un calendario .ics que se pueda leer."""
