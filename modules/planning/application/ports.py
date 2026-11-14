"""Ports de planning: lo que los casos de uso necesitan de la persistencia.

Cada repositorio se construye ya ligado a un `user_id`, así que los casos de uso no lo manejan.
`guardar` es un upsert por `id`: sirve para crear y para actualizar.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Protocol

from modules.planning.domain.eventos import BloqueRecurrente, Evento, LecturaCalendario
from modules.planning.domain.tareas import Tarea


class RepositorioTareas(Protocol):
    """Tareas del usuario."""

    def guardar(self, tarea: Tarea) -> None:
        """Inserta la tarea o la sustituye si ya existe una con su `id`."""
        ...

    def obtener(self, tarea_id: str) -> Tarea | None: ...

    def del_dia(self, dia: date) -> list[Tarea]:
        """Tareas con `fecha == dia`, hechas o no."""
        ...

    def atrasadas(self, dia: date) -> list[Tarea]:
        """Tareas pendientes con fecha anterior a `dia`."""
        ...

    def sin_fecha(self) -> list[Tarea]:
        """Tareas sin día asignado (bandeja de entrada), hechas o no."""
        ...

    def borrar(self, tarea_id: str) -> bool:
        """Borra la tarea; devuelve False si no existía."""
        ...


class RepositorioEventos(Protocol):
    """Eventos puntuales del usuario."""

    def guardar(self, evento: Evento) -> None:
        """Inserta el evento o lo sustituye si ya existe uno con su `id`."""
        ...

    def obtener(self, evento_id: str) -> Evento | None: ...

    def por_uid(self, uid_externo: str) -> Evento | None:
        """Evento importado de un .ics con ese UID, si existe."""
        ...

    def entre(self, inicio: datetime, fin: datetime) -> list[Evento]:
        """Eventos que se pisan con [inicio, fin), ordenados por inicio."""
        ...

    def borrar(self, evento_id: str) -> bool:
        """Borra el evento; devuelve False si no existía."""
        ...


class RepositorioBloques(Protocol):
    """Bloques recurrentes semanales del usuario."""

    def guardar(self, bloque: BloqueRecurrente) -> None:
        """Inserta el bloque o lo sustituye si ya existe uno con su `id`."""
        ...

    def obtener(self, bloque_id: str) -> BloqueRecurrente | None: ...

    def listar(self) -> list[BloqueRecurrente]:
        """Todos los bloques, por día de la semana y hora de inicio."""
        ...

    def borrar(self, bloque_id: str) -> bool:
        """Borra el bloque; devuelve False si no existía."""
        ...


class LectorCalendario(Protocol):
    """Convierte un fichero de calendario (.ics) en eventos de planning."""

    def leer(self, contenido: bytes, desde: date, hasta: date) -> LecturaCalendario:
        """Eventos que empiezan entre `desde` y `hasta` (incluidos); lanza CalendarioInvalido."""
        ...
