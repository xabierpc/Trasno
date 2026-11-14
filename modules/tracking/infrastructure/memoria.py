"""Repositorios en memoria de tracking: para tests y para probar sin base de datos."""

from __future__ import annotations

from dataclasses import replace
from datetime import date

from modules.tracking.domain.errores import MetricaDuplicada
from modules.tracking.domain.metricas import MetricDefinition, MetricEntry

type _Clave = tuple[str, date, int]


class RepositorioMetricasMemoria:
    """Implementa `RepositorioMetricas` sobre un diccionario."""

    def __init__(self) -> None:
        self._por_nombre: dict[str, MetricDefinition] = {}

    def guardar(self, definicion: MetricDefinition) -> None:
        if definicion.nombre in self._por_nombre:
            raise MetricaDuplicada(definicion.nombre)
        self._por_nombre[definicion.nombre] = definicion

    def actualizar(self, definicion: MetricDefinition) -> None:
        self._por_nombre[definicion.nombre] = definicion

    def por_nombre(self, nombre: str) -> MetricDefinition | None:
        return self._por_nombre.get(nombre)

    def listar(self) -> list[MetricDefinition]:
        return sorted(self._por_nombre.values(), key=lambda d: d.nombre)


class RepositorioEntradasMemoria:
    """Implementa `RepositorioEntradas` sobre un diccionario con la clave única como índice."""

    def __init__(self) -> None:
        self._entradas: dict[_Clave, MetricEntry] = {}

    def guardar(self, entrada: MetricEntry) -> MetricEntry:
        clave = (entrada.metric_id, entrada.logical_date, entrada.slot)
        existente = self._entradas.get(clave)
        if existente is not None:
            entrada = replace(entrada, id=existente.id)
        self._entradas[clave] = entrada
        return entrada

    def siguiente_slot(self, metric_id: str, logical_date: date) -> int:
        slots = [s for (m, f, s) in self._entradas if m == metric_id and f == logical_date]
        return max(slots, default=-1) + 1

    def listar(self, metric_id: str, desde: date, hasta: date) -> list[MetricEntry]:
        return sorted(
            (
                e
                for e in self._entradas.values()
                if e.metric_id == metric_id and desde <= e.logical_date <= hasta
            ),
            key=lambda e: (e.logical_date, e.slot),
        )

    def borrar(self, entrada_id: str) -> bool:
        for clave, entrada in self._entradas.items():
            if entrada.id == entrada_id:
                del self._entradas[clave]
                return True
        return False
