"""Datos de arranque de tracking: métricas que existen nada más instalar.

`trasno migrate` llama a `datos_arranque` en cada ejecución, así que es idempotente:
una métrica que ya existe (aunque el usuario la haya cambiado) no se toca.
"""

from __future__ import annotations

from sqlalchemy import Engine

from core.config import Settings
from modules.tracking.domain.metricas import (
    Agregacion,
    MetricDefinition,
    PoliticaDuplicado,
    TipoMetrica,
)
from modules.tracking.infrastructure.repositorios import RepositorioMetricasSQL


def metricas_iniciales() -> list[MetricDefinition]:
    """Definiciones que se crean al migrar si todavía no existen."""
    return [
        MetricDefinition(
            nombre="peso",
            unidad="kg",
            tipo=TipoMetrica.NUMERICA,
            agregacion=Agregacion.MEDIA,
            on_duplicate=PoliticaDuplicado.REPLACE,
        ),
    ]


def datos_arranque(engine: Engine) -> None:
    """Crea las métricas iniciales que falten para el usuario configurado."""
    metricas = RepositorioMetricasSQL(engine, Settings().user_id)
    for definicion in metricas_iniciales():
        if metricas.por_nombre(definicion.nombre) is None:
            metricas.guardar(definicion)
