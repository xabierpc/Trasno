"""Casos de uso de analytics: catálogo de series, unión por fecha, medias móviles y correlación.

Analytics no importa ningún módulo: lee las series a través de `SeriesProvider` (core.contracts).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import date

import pandas as pd

from core.contracts import SeriesInfo, SeriesProvider
from modules.analytics.domain.errores import SerieDuplicada, SerieNoEncontrada

Puntos = list[tuple[date, float]]


class CatalogoSeries:
    """Reúne las series de todos los proveedores; los consulta en cada llamada."""

    def __init__(self, proveedores: Callable[[], Sequence[SeriesProvider]]) -> None:
        self._proveedores = proveedores

    def listar(self) -> list[SeriesInfo]:
        """Lista todas las series disponibles, en orden de registro del proveedor."""
        return [info for p in self._proveedores() for info in p.list_series()]

    def obtener(self, nombre: str, desde: date, hasta: date) -> Puntos:
        """Devuelve los puntos de la serie `nombre` entre `desde` y `hasta`."""
        return self._proveedor_de(nombre).get_series(nombre, desde, hasta)

    def tabla(self, nombres: Sequence[str], desde: date, hasta: date) -> pd.DataFrame:
        """Une las series `nombres` entre `desde` y `hasta` en un DataFrame por fecha."""
        return unir_series({nombre: self.obtener(nombre, desde, hasta) for nombre in nombres})

    def _proveedor_de(self, nombre: str) -> SeriesProvider:
        candidatos = [
            p for p in self._proveedores() if any(s.nombre == nombre for s in p.list_series())
        ]
        if not candidatos:
            raise SerieNoEncontrada(nombre)
        if len(candidatos) > 1:
            raise SerieDuplicada(nombre)
        return candidatos[0]


def unir_series(series: Mapping[str, Puntos]) -> pd.DataFrame:
    """Outer join por fecha: una columna por serie, índice `fecha` ordenado y NaN en los huecos."""
    columnas = [
        pd.Series(
            [valor for _, valor in puntos],
            index=pd.DatetimeIndex([fecha for fecha, _ in puntos]),
            name=nombre,
            dtype="float64",
        )
        for nombre, puntos in series.items()
    ]
    tabla = pd.concat(columnas, axis=1, join="outer", sort=False).sort_index()
    tabla.index.name = "fecha"
    return tabla


def medias_moviles(tabla: pd.DataFrame, dias: int) -> pd.DataFrame:
    """Media móvil de cada columna en una ventana de `dias` días de calendario (ignora NaN)."""
    return tabla.rolling(f"{dias}D", min_periods=1).mean()


def correlacion(tabla: pd.DataFrame, min_puntos: int = 2) -> pd.DataFrame:
    """Correlación de Pearson entre columnas, con solo las fechas comunes a cada par."""
    return tabla.corr(min_periods=min_puntos)
