"""Agenda de un día: citas (eventos y bloques) y tareas, en hora local.

Es un cálculo puro: recibe lo ya leído de los repositorios y lo ordena. No se guarda.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo

from modules.planning.domain.eventos import BloqueRecurrente, Evento
from modules.planning.domain.tareas import Prioridad, Tarea

_ORDEN_PRIORIDAD = {Prioridad.ALTA: 0, Prioridad.MEDIA: 1, Prioridad.BAJA: 2}


class TipoCita(StrEnum):
    EVENTO = "evento"
    BLOQUE = "bloque"


@dataclass(frozen=True)
class Cita:
    """Algo con hora en la agenda. `id` es el del evento o el del bloque del que sale."""

    titulo: str
    inicio: datetime
    fin: datetime
    tipo: TipoCita
    id: str
    lugar: str | None = None


@dataclass(frozen=True)
class Agenda:
    """Lo que hay un día: citas por hora, tareas del día y tareas atrasadas sin hacer."""

    dia: date
    citas: list[Cita]
    tareas: list[Tarea]
    atrasadas: list[Tarea]


def limites_del_dia(dia: date, zona: str) -> tuple[datetime, datetime]:
    """[inicio, fin) del día en hora local: de las 00:00 de `dia` a las 00:00 del siguiente."""
    tz = ZoneInfo(zona)
    return (
        datetime.combine(dia, time(0), tzinfo=tz),
        datetime.combine(dia + timedelta(days=1), time(0), tzinfo=tz),
    )


def orden_de_tareas(tarea: Tarea) -> tuple[bool, int, str]:
    """Pendientes antes que hechas; dentro, por prioridad (alta primero) y título."""
    return (tarea.hecha, _ORDEN_PRIORIDAD[tarea.prioridad], tarea.titulo.lower())


def agenda_del_dia(
    dia: date,
    zona: str,
    eventos: Iterable[Evento],
    bloques: Iterable[BloqueRecurrente],
    tareas: Iterable[Tarea],
    atrasadas: Iterable[Tarea] = (),
) -> Agenda:
    """Monta la agenda de `dia`. Los eventos que cruzan la medianoche salen en los dos días."""
    inicio, fin = limites_del_dia(dia, zona)
    tz = ZoneInfo(zona)
    citas = [
        Cita(
            titulo=e.titulo,
            inicio=e.inicio.astimezone(tz),
            fin=e.fin.astimezone(tz),
            tipo=TipoCita.EVENTO,
            id=e.id,
            lugar=e.lugar,
        )
        for e in eventos
        if e.inicio < fin and inicio < e.fin
    ]
    citas += [
        Cita(
            titulo=o.titulo,
            inicio=o.inicio,
            fin=o.fin,
            tipo=TipoCita.BLOQUE,
            id=o.bloque_id,
            lugar=o.lugar,
        )
        for bloque in bloques
        for o in bloque.ocurrencias(dia, dia, zona)
    ]
    citas.sort(key=lambda c: (c.inicio, c.fin, c.titulo))
    return Agenda(
        dia=dia,
        citas=citas,
        tareas=sorted((t for t in tareas if t.fecha == dia), key=orden_de_tareas),
        atrasadas=sorted(
            (t for t in atrasadas if not t.hecha and t.fecha is not None and t.fecha < dia),
            key=lambda t: (t.fecha, *orden_de_tareas(t)),
        ),
    )
