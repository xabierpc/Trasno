"""Módulo tracking: métricas genéricas configurables y sus entradas diarias."""

from __future__ import annotations

from core.contracts import AppContext
from modules.tracking.api import crear_router
from modules.tracking.application.briefing import SeccionBriefingTracking
from modules.tracking.application.casos_uso import CasosUsoTracking
from modules.tracking.application.series import ProveedorSeriesTracking
from modules.tracking.domain.eventos import MetricaRegistrada
from modules.tracking.infrastructure.repositorios import (
    RepositorioEntradasSQL,
    RepositorioMetricasSQL,
)


def register(ctx: AppContext) -> None:
    """Enchufa tracking: router /tracking, proveedor de series y evento MetricaRegistrada."""
    engine = ctx.engine_factory("tracking")
    metricas = RepositorioMetricasSQL(engine, ctx.settings.user_id)
    entradas = RepositorioEntradasSQL(engine, ctx.settings.user_id)
    casos = CasosUsoTracking(
        metricas,
        entradas,
        # Los repositorios ya han hecho commit cuando avisan: el evento sale con el dato guardado.
        al_registrar=lambda definicion, entrada: ctx.bus.publish(
            MetricaRegistrada(
                metrica=definicion.nombre,
                entrada_id=entrada.id,
                valor=entrada.valor,
                logical_date=entrada.logical_date,
            )
        ),
    )
    ctx.add_router(crear_router(casos, ctx.settings))
    ctx.add_series_provider(ProveedorSeriesTracking(metricas, entradas))
    ctx.add_briefing_section(SeccionBriefingTracking(casos))
