"""Proveedor de series de tracking: expone cada métrica no categórica a analytics."""

from __future__ import annotations

from datetime import date

from core.contracts import SeriesInfo
from modules.tracking.application.ports import RepositorioEntradas, RepositorioMetricas
from modules.tracking.domain.errores import MetricaNoEncontrada
from modules.tracking.domain.metricas import MetricDefinition, TipoMetrica
from modules.tracking.domain.series import agregar_por_dia


class ProveedorSeriesTracking:
    """Implementa `core.contracts.SeriesProvider`; el nombre de la serie es el de la métrica."""

    def __init__(self, metricas: RepositorioMetricas, entradas: RepositorioEntradas) -> None:
        self._metricas = metricas
        self._entradas = entradas

    def list_series(self) -> list[SeriesInfo]:
        """Una serie por métrica con lectura numérica (todas menos las categóricas)."""
        return [
            SeriesInfo(nombre=m.nombre, unidad=m.unidad, descripcion=f"Métrica {m.tipo.value}")
            for m in self._metricas.listar()
            if _tiene_serie(m)
        ]

    def get_series(self, nombre: str, desde: date, hasta: date) -> list[tuple[date, float]]:
        """Un valor por día lógico entre `desde` y `hasta`, agregado según la métrica."""
        metrica = self._metricas.por_nombre(nombre)
        if metrica is None or not _tiene_serie(metrica):
            raise MetricaNoEncontrada(nombre)
        return agregar_por_dia(self._entradas.listar(metrica.id, desde, hasta), metrica.agregacion)


def _tiene_serie(metrica: MetricDefinition) -> bool:
    return metrica.tipo is not TipoMetrica.CATEGORICA
