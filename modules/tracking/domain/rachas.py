"""Rachas y cumplimiento de una métrica. Se calculan al pedirlos: nunca se guardan.

Un día está **cumplido** según la métrica:

| Métrica                 | Día cumplido cuando…                       |
|-------------------------|--------------------------------------------|
| booleana                | el valor del día es `true`                 |
| con objetivo            | el valor agregado del día >= objetivo      |
| sin objetivo            | hay algún registro ese día                 |

`hoy` nunca rompe la racha: si todavía no está cumplido, se cuenta hasta ayer.
"""

from __future__ import annotations

from collections.abc import Iterable, Set
from dataclasses import dataclass
from datetime import date, timedelta

from modules.tracking.domain.metricas import MetricDefinition, MetricEntry, TipoMetrica
from modules.tracking.domain.series import agregar_por_dia

DIAS_SEMANA = 7
DIAS_MES = 30
_UN_DIA = timedelta(days=1)


@dataclass(frozen=True)
class Racha:
    """Días cumplidos seguidos: la racha en curso y la más larga hasta hoy."""

    actual: int
    maxima: int


@dataclass(frozen=True)
class Cumplimiento:
    """Días cumplidos dentro de una ventana de `dias` días que termina hoy."""

    cumplidos: int
    dias: int

    @property
    def porcentaje(self) -> float:
        return round(100 * self.cumplidos / self.dias, 1)


@dataclass(frozen=True)
class ResumenRacha:
    """Todo lo que se muestra de una métrica: racha y cumplimiento semanal y mensual."""

    metrica: str
    racha: Racha
    semanal: Cumplimiento
    mensual: Cumplimiento


def dias_cumplidos(definicion: MetricDefinition, entradas: Iterable[MetricEntry]) -> set[date]:
    """Días lógicos en los que la métrica se da por cumplida (ver tabla del módulo)."""
    if definicion.tipo is TipoMetrica.CATEGORICA:
        return {e.logical_date for e in entradas}
    por_dia = agregar_por_dia(entradas, definicion.agregacion)
    if definicion.tipo is TipoMetrica.BOOLEANA:
        return {dia for dia, valor in por_dia if valor > 0}
    if definicion.objetivo is not None:
        return {dia for dia, valor in por_dia if valor >= definicion.objetivo}
    return {dia for dia, _ in por_dia}


def calcular_racha(cumplidos: Set[date], hoy: date) -> Racha:
    """Racha actual (hasta hoy, o hasta ayer si hoy aún no está cumplido) y racha máxima."""
    pasados = sorted(dia for dia in cumplidos if dia <= hoy)
    maxima = seguidos = 0
    anterior: date | None = None
    for dia in pasados:
        seguidos = seguidos + 1 if anterior is not None and dia - anterior == _UN_DIA else 1
        maxima = max(maxima, seguidos)
        anterior = dia

    actual = 0
    dia = hoy if hoy in cumplidos else hoy - _UN_DIA
    while dia in cumplidos:
        actual += 1
        dia -= _UN_DIA
    return Racha(actual=actual, maxima=maxima)


def cumplimiento(cumplidos: Set[date], hoy: date, dias: int) -> Cumplimiento:
    """Cuántos de los últimos `dias` días (hoy incluido) están cumplidos."""
    desde = hoy - timedelta(days=dias - 1)
    return Cumplimiento(cumplidos=sum(desde <= dia <= hoy for dia in cumplidos), dias=dias)


def resumir_racha(
    definicion: MetricDefinition, entradas: Iterable[MetricEntry], hoy: date
) -> ResumenRacha:
    """Racha y cumplimiento de 7 y 30 días de la métrica, vistos desde `hoy`."""
    cumplidos = dias_cumplidos(definicion, entradas)
    return ResumenRacha(
        metrica=definicion.nombre,
        racha=calcular_racha(cumplidos, hoy),
        semanal=cumplimiento(cumplidos, hoy, DIAS_SEMANA),
        mensual=cumplimiento(cumplidos, hoy, DIAS_MES),
    )
