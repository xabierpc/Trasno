"""Eventos puntuales y bloques recurrentes del horario, y detección de solapes.

Un `Evento` es un intervalo concreto (una reunión, un examen, una clase importada del .ics).
Un `BloqueRecurrente` se repite cada semana (p. ej. clase los lunes de 9:00 a 11:00) y se
expande en `Ocurrencia`s al pedir la agenda de un rango de días; las ocurrencias no se guardan.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo

from modules.planning.domain.errores import BloqueInvalido, EventoInvalido


class OrigenEvento(StrEnum):
    """De dónde viene un evento. Los valores se guardan en la BD: no cambiarlos."""

    MANUAL = "manual"
    ICS = "ics"


def _nuevo_id() -> str:
    return str(uuid.uuid4())


def _con_zona(instante: datetime) -> bool:
    return instante.tzinfo is not None and instante.utcoffset() is not None


def _limpiar(titulo: str) -> str:
    return " ".join(titulo.split())


@dataclass(frozen=True, kw_only=True)
class Evento:
    """Un intervalo concreto en el calendario. `uid_externo` identifica el evento en su .ics."""

    titulo: str
    inicio: datetime
    fin: datetime
    lugar: str | None = None
    origen: OrigenEvento = OrigenEvento.MANUAL
    uid_externo: str | None = None
    id: str = field(default_factory=_nuevo_id)

    def __post_init__(self) -> None:
        object.__setattr__(self, "titulo", _limpiar(self.titulo))
        if not self.titulo:
            raise EventoInvalido("El título del evento no puede estar vacío")
        if not (_con_zona(self.inicio) and _con_zona(self.fin)):
            raise EventoInvalido("`inicio` y `fin` deben llevar zona horaria")
        if self.fin <= self.inicio:
            raise EventoInvalido(f"El evento {self.titulo!r} debe terminar después de empezar")
        if self.origen is OrigenEvento.ICS and not self.uid_externo:
            raise EventoInvalido("Un evento importado de un .ics necesita `uid_externo`")


@dataclass(frozen=True, kw_only=True)
class BloqueRecurrente:
    """Un hueco que se repite cada semana, en hora local. `dia_semana`: 0 = lunes … 6 = domingo.

    `desde` y `hasta` (incluidos) limitan el periodo en que se repite, p. ej. un cuatrimestre.
    """

    titulo: str
    dia_semana: int
    hora_inicio: time
    hora_fin: time
    desde: date | None = None
    hasta: date | None = None
    lugar: str | None = None
    id: str = field(default_factory=_nuevo_id)

    def __post_init__(self) -> None:
        object.__setattr__(self, "titulo", _limpiar(self.titulo))
        if not self.titulo:
            raise BloqueInvalido("El título del bloque no puede estar vacío")
        if not (
            isinstance(self.dia_semana, int)
            and not isinstance(self.dia_semana, bool)
            and 0 <= self.dia_semana <= 6
        ):
            raise BloqueInvalido(f"El día de la semana va de 0 (lunes) a 6: {self.dia_semana!r}")
        if self.hora_fin <= self.hora_inicio:
            raise BloqueInvalido(f"El bloque {self.titulo!r} debe terminar después de empezar")
        if self.desde and self.hasta and self.hasta < self.desde:
            raise BloqueInvalido("`hasta` no puede ser anterior a `desde`")

    def ocurrencias(self, desde: date, hasta: date, zona: str) -> list[Ocurrencia]:
        """Expande el bloque en los días de [desde, hasta] (incluidos), en la zona dada."""
        tz = ZoneInfo(zona)
        primero = max(desde, self.desde) if self.desde else desde
        ultimo = min(hasta, self.hasta) if self.hasta else hasta
        dia = primero + timedelta(days=(self.dia_semana - primero.weekday()) % 7)
        resultado: list[Ocurrencia] = []
        while dia <= ultimo:
            resultado.append(
                Ocurrencia(
                    titulo=self.titulo,
                    inicio=datetime.combine(dia, self.hora_inicio, tzinfo=tz),
                    fin=datetime.combine(dia, self.hora_fin, tzinfo=tz),
                    lugar=self.lugar,
                    bloque_id=self.id,
                )
            )
            dia += timedelta(days=7)
        return resultado


@dataclass(frozen=True, kw_only=True)
class Ocurrencia:
    """Una repetición concreta de un bloque recurrente. Se calcula, no se guarda."""

    titulo: str
    inicio: datetime
    fin: datetime
    bloque_id: str
    lugar: str | None = None


Intervalo = Evento | Ocurrencia


def se_solapan(a: Intervalo, b: Intervalo) -> bool:
    """Dos intervalos se solapan si comparten algún instante. Tocarse (9-10 y 10-11) no cuenta."""
    return a.inicio < b.fin and b.inicio < a.fin


@dataclass(frozen=True)
class Solape:
    """Aviso: el intervalo nuevo se pisa con otro que ya está en el horario."""

    titulo: str
    inicio: datetime
    fin: datetime


def _mismo_evento(a: Intervalo, b: Intervalo) -> bool:
    """Al editar un evento no hay que avisar de que se solapa consigo mismo."""
    return isinstance(a, Evento) and isinstance(b, Evento) and a.id == b.id


def solapes(nuevo: Intervalo, existentes: Iterable[Intervalo]) -> list[Solape]:
    """Avisos de solape de `nuevo` con `existentes`, ordenados por inicio. No impide guardar."""
    pisados = [e for e in existentes if se_solapan(nuevo, e) and not _mismo_evento(nuevo, e)]
    pisados.sort(key=lambda e: e.inicio)
    return [Solape(titulo=e.titulo, inicio=e.inicio, fin=e.fin) for e in pisados]


def bloques_se_solapan(a: BloqueRecurrente, b: BloqueRecurrente) -> bool:
    """Mismo día de la semana, horas que se pisan y periodos (desde/hasta) que coinciden."""
    if a.id == b.id or a.dia_semana != b.dia_semana:
        return False
    if not (a.hora_inicio < b.hora_fin and b.hora_inicio < a.hora_fin):
        return False
    a_desde, a_hasta = a.desde or date.min, a.hasta or date.max
    b_desde, b_hasta = b.desde or date.min, b.hasta or date.max
    return a_desde <= b_hasta and b_desde <= a_hasta
