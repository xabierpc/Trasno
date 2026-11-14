"""Módulo briefing: resumen diario con lo que aporta cada módulo, a una hora fija."""

from __future__ import annotations

from core.contracts import AppContext, CadaDia
from modules.briefing.api import crear_router
from modules.briefing.application.casos_uso import CasosUsoBriefing
from modules.briefing.infrastructure.notificador import NotificadorEscritorio


def register(ctx: AppContext) -> None:
    """Enchufa el briefing: router /briefing y trabajo diario a `Settings.briefing_hora`."""
    casos = CasosUsoBriefing(
        ctx.briefing_sections, zona=ctx.settings.timezone, notificador=NotificadorEscritorio()
    )
    ctx.add_router(crear_router(casos))
    ctx.add_job("briefing.diario", casos.enviar_briefing, CadaDia(ctx.settings.briefing_hora))
