"""Proveedor de series de training: volumen semanal y 1RM estimado de cada ejercicio."""

from __future__ import annotations

from datetime import date

from core.contracts import SeriesInfo
from modules.training.application.casos_uso import CasosUsoTraining
from modules.training.domain.errores import EjercicioNoEncontrado, SerieTemporalNoEncontrada

VOLUMEN_SEMANAL = "volumen_semanal"
PREFIJO_1RM = "1rm "


class ProveedorSeriesTraining:
    """Implementa `core.contracts.SeriesProvider` sobre los casos de uso de training."""

    def __init__(self, casos: CasosUsoTraining) -> None:
        self._casos = casos

    def list_series(self) -> list[SeriesInfo]:
        """`volumen_semanal` y una serie `1rm <ejercicio>` por cada ejercicio registrado."""
        volumen = SeriesInfo(
            nombre=VOLUMEN_SEMANAL,
            unidad="kg",
            descripcion="Volumen de entreno de cada semana, fechado en su lunes",
        )
        return [volumen] + [
            SeriesInfo(
                nombre=f"{PREFIJO_1RM}{ejercicio}",
                unidad="kg",
                descripcion=f"1RM estimado (Epley) de {ejercicio}",
            )
            for ejercicio in self._casos.listar_ejercicios()
        ]

    def get_series(self, nombre: str, desde: date, hasta: date) -> list[tuple[date, float]]:
        """Puntos (fecha lógica, valor) de la serie entre `desde` y `hasta`."""
        if nombre == VOLUMEN_SEMANAL:
            return self._casos.volumen_semanal(desde, hasta)
        if not nombre.startswith(PREFIJO_1RM):
            raise SerieTemporalNoEncontrada(nombre)
        try:
            puntos = self._casos.progreso_ejercicio(nombre.removeprefix(PREFIJO_1RM), desde, hasta)
        except EjercicioNoEncontrado as error:
            raise SerieTemporalNoEncontrada(nombre) from error
        return [(p.logical_date, p.un_rm) for p in puntos]
