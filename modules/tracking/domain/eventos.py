"""Eventos de dominio que publica tracking en el bus."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from core.contracts import Event
from modules.tracking.domain.metricas import ValorMetrica


@dataclass(frozen=True, kw_only=True)
class MetricaRegistrada(Event):
    """Se ha guardado (o sobrescrito) un valor de una métrica."""

    metrica: str
    entrada_id: str
    valor: ValorMetrica
    logical_date: date
