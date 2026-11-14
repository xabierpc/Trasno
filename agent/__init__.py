"""Agente de Trasno: un LLM que usa como herramientas los casos de uso de los módulos."""

from __future__ import annotations

from agent.agente import Agente
from agent.api import crear_router
from agent.llm_openai import LLMOpenAICompatible
from agent.mensajes import LLM
from core.contracts import AppContext, Settings


def crear_llm(settings: Settings) -> LLM:
    """El LLM configurado en `Settings` (se sustituye en los tests por uno falso)."""
    return LLMOpenAICompatible(settings.llm_url, settings.llm_modelo)


def register(ctx: AppContext) -> None:
    """Enchufa el agente: router /agent sobre las herramientas que hayan registrado los módulos."""
    agente = Agente(
        crear_llm(ctx.settings),
        herramientas=ctx.tools,
        acciones=lambda: ctx.acciones,
        zona=ctx.settings.timezone,
        ventana_madrugada=ctx.settings.ventana_madrugada,
    )
    ctx.add_router(crear_router(agente, ctx.tools, lambda: ctx.acciones))
