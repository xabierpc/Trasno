"""Módulo training: sesiones de entreno con sus ejercicios y series."""

from __future__ import annotations

from core.contracts import AppContext
from modules.training.api import crear_router
from modules.training.application.briefing import SeccionBriefingTraining
from modules.training.application.casos_uso import CasosUsoTraining
from modules.training.application.series import ProveedorSeriesTraining
from modules.training.domain.eventos import SesionBorrada, SesionRegistrada
from modules.training.infrastructure.repositorios import RepositorioSesionesSQL


def register(ctx: AppContext) -> None:
    """Enchufa training: router /training, proveedor de series y eventos de sesión."""
    sesiones = RepositorioSesionesSQL(ctx.engine_factory("training"), ctx.settings.user_id)
    casos = CasosUsoTraining(
        sesiones,
        # El repositorio ya ha hecho commit cuando avisa: el evento sale con el dato guardado.
        al_registrar=lambda sesion: ctx.bus.publish(
            SesionRegistrada(
                sesion_id=sesion.id,
                logical_date=sesion.logical_date,
                tipo=sesion.tipo,
                volumen=sesion.volumen,
            )
        ),
        al_borrar=lambda sesion_id: ctx.bus.publish(SesionBorrada(sesion_id=sesion_id)),
    )
    ctx.add_router(crear_router(casos))
    ctx.add_series_provider(ProveedorSeriesTraining(casos))
    ctx.add_briefing_section(SeccionBriefingTraining(casos))
