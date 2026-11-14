"""Módulo planning: tareas, eventos, bloques recurrentes y agenda del día."""

from __future__ import annotations

from core.contracts import AppContext
from modules.planning.api import crear_router
from modules.planning.application.briefing import SeccionBriefingPlanning
from modules.planning.application.casos_uso import CasosUsoPlanning
from modules.planning.application.herramientas import herramientas_planning
from modules.planning.infrastructure.ics import LectorIcs
from modules.planning.infrastructure.repositorios import (
    RepositorioBloquesSQL,
    RepositorioEventosSQL,
    RepositorioTareasSQL,
)


def register(ctx: AppContext) -> None:
    """Enchufa planning: router /planning sobre planning.sqlite y su sección del briefing."""
    engine = ctx.engine_factory("planning")
    user_id = ctx.settings.user_id
    casos = CasosUsoPlanning(
        RepositorioTareasSQL(engine, user_id),
        RepositorioEventosSQL(engine, user_id),
        RepositorioBloquesSQL(engine, user_id),
        zona=ctx.settings.timezone,
        lector=LectorIcs(ctx.settings.timezone),
    )
    ctx.add_router(crear_router(casos, ctx.settings))
    ctx.add_briefing_section(SeccionBriefingPlanning(casos))
    for tool in herramientas_planning(casos, ctx.settings.timezone):
        ctx.add_tool(tool)
