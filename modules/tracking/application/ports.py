"""Ports de tracking: lo que los casos de uso necesitan de la persistencia.

Cada repositorio se construye ya ligado a un `user_id`, así que los casos de uso no lo manejan.
"""

from __future__ import annotations

from datetime import date
from typing import Protocol

from modules.tracking.domain.metricas import MetricDefinition, MetricEntry


class RepositorioMetricas(Protocol):
    """Definiciones de métricas del usuario; el nombre es único."""

    def guardar(self, definicion: MetricDefinition) -> None:
        """Inserta la definición; lanza `MetricaDuplicada` si el nombre ya existe."""
        ...

    def actualizar(self, definicion: MetricDefinition) -> None:
        """Sobrescribe la configuración de la métrica que ya existe con ese id."""
        ...

    def por_nombre(self, nombre: str) -> MetricDefinition | None:
        """Devuelve la métrica con ese nombre o None."""
        ...

    def listar(self) -> list[MetricDefinition]:
        """Devuelve todas las métricas ordenadas por nombre."""
        ...


class RepositorioEntradas(Protocol):
    """Entradas de las métricas; (metric_id, logical_date, slot) es único."""

    def guardar(self, entrada: MetricEntry) -> MetricEntry:
        """Upsert por (metric_id, logical_date, slot); si ya existía conserva su id."""
        ...

    def siguiente_slot(self, metric_id: str, logical_date: date) -> int:
        """Primer slot libre de la métrica en ese día lógico (0 si no hay entradas)."""
        ...

    def listar(self, metric_id: str, desde: date, hasta: date) -> list[MetricEntry]:
        """Entradas con logical_date en [desde, hasta], ordenadas por fecha y slot."""
        ...

    def borrar(self, entrada_id: str) -> bool:
        """Borra la entrada; devuelve False si no existía."""
        ...
