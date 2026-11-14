"""Repositorios en memoria de planning: para tests y para probar sin base de datos."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime

from modules.planning.domain.eventos import BloqueRecurrente, Evento
from modules.planning.domain.tareas import Tarea


class RepositorioTareasMemoria:
    """Implementa `RepositorioTareas` sobre un diccionario."""

    def __init__(self) -> None:
        self._tareas: dict[str, Tarea] = {}

    def guardar(self, tarea: Tarea) -> None:
        self._tareas[tarea.id] = tarea

    def obtener(self, tarea_id: str) -> Tarea | None:
        return self._tareas.get(tarea_id)

    def del_dia(self, dia: date) -> list[Tarea]:
        return self._ordenadas(t for t in self._tareas.values() if t.fecha == dia)

    def atrasadas(self, dia: date) -> list[Tarea]:
        return self._ordenadas(
            t
            for t in self._tareas.values()
            if not t.hecha and t.fecha is not None and t.fecha < dia
        )

    def sin_fecha(self) -> list[Tarea]:
        return self._ordenadas(t for t in self._tareas.values() if t.fecha is None)

    def borrar(self, tarea_id: str) -> bool:
        return self._tareas.pop(tarea_id, None) is not None

    @staticmethod
    def _ordenadas(tareas: Iterable[Tarea]) -> list[Tarea]:
        return sorted(tareas, key=lambda t: (t.fecha or date.min, t.creada_en))


class RepositorioEventosMemoria:
    """Implementa `RepositorioEventos` sobre un diccionario."""

    def __init__(self) -> None:
        self._eventos: dict[str, Evento] = {}

    def guardar(self, evento: Evento) -> None:
        self._eventos[evento.id] = evento

    def obtener(self, evento_id: str) -> Evento | None:
        return self._eventos.get(evento_id)

    def por_uid(self, uid_externo: str) -> Evento | None:
        return next((e for e in self._eventos.values() if e.uid_externo == uid_externo), None)

    def entre(self, inicio: datetime, fin: datetime) -> list[Evento]:
        return sorted(
            (e for e in self._eventos.values() if e.inicio < fin and inicio < e.fin),
            key=lambda e: (e.inicio, e.fin),
        )

    def borrar(self, evento_id: str) -> bool:
        return self._eventos.pop(evento_id, None) is not None


class RepositorioBloquesMemoria:
    """Implementa `RepositorioBloques` sobre un diccionario."""

    def __init__(self) -> None:
        self._bloques: dict[str, BloqueRecurrente] = {}

    def guardar(self, bloque: BloqueRecurrente) -> None:
        self._bloques[bloque.id] = bloque

    def obtener(self, bloque_id: str) -> BloqueRecurrente | None:
        return self._bloques.get(bloque_id)

    def listar(self) -> list[BloqueRecurrente]:
        return sorted(self._bloques.values(), key=lambda b: (b.dia_semana, b.hora_inicio))

    def borrar(self, bloque_id: str) -> bool:
        return self._bloques.pop(bloque_id, None) is not None
