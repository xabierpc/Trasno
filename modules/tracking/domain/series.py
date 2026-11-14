"""Resumen diario de una métrica: un valor por día lógico según su agregación."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from itertools import groupby

from modules.tracking.domain.metricas import Agregacion, MetricEntry


def agregar_por_dia(
    entradas: Iterable[MetricEntry], agregacion: Agregacion
) -> list[tuple[date, float]]:
    """Devuelve (día, valor) ordenado por día; las entradas deben ser numéricas o booleanas."""
    ordenadas = sorted(entradas, key=lambda e: (e.logical_date, e.slot))
    return [
        (dia, _agregar([float(e.valor) for e in grupo], agregacion))
        for dia, grupo in groupby(ordenadas, key=lambda e: e.logical_date)
    ]


def _agregar(valores: list[float], agregacion: Agregacion) -> float:
    match agregacion:
        case Agregacion.SUMA:
            return sum(valores)
        case Agregacion.MEDIA:
            return sum(valores) / len(valores)
        case Agregacion.ULTIMA:
            return valores[-1]
