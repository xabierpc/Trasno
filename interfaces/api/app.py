"""App factory de FastAPI: carga los módulos y monta sus routers."""

from __future__ import annotations

from collections.abc import Sequence
from importlib.metadata import version
from typing import Literal

from fastapi import FastAPI, Request
from pydantic import BaseModel

from core.bus import InMemoryEventBus
from core.config import Settings
from core.context import ContextoApp
from core.db import make_engine
from core.loader import cargar_modulos


class Health(BaseModel):
    """Estado de la API: versión de Trasno y módulos registrados."""

    status: Literal["ok"] = "ok"
    version: str
    modulos: list[str]


def create_app(
    ctx: ContextoApp | None = None,
    paquete_modulos: str = "modules",
    extras: Sequence[str] = ("agent",),
) -> FastAPI:
    """Crea la app: registra los módulos en `ctx` y monta los routers que hayan añadido."""
    ctx = ctx or _contexto_por_defecto()
    modulos = cargar_modulos(ctx, paquete_modulos=paquete_modulos, extras=extras)

    app = FastAPI(title="Trasno", version=version("trasno"))
    app.state.ctx = ctx
    app.state.modulos = modulos
    app.add_api_route("/health", health, methods=["GET"], response_model=Health)
    for router in ctx.routers:
        app.include_router(router)
    return app


def health(request: Request) -> Health:
    """Devuelve la versión y los módulos cargados."""
    return Health(version=request.app.version, modulos=request.app.state.modulos)


def _contexto_por_defecto() -> ContextoApp:
    return ContextoApp(bus=InMemoryEventBus(), engine_factory=make_engine, settings=Settings())
