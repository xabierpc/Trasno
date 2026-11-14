"""App factory de FastAPI: carga los módulos y monta sus routers."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from importlib.metadata import version
from typing import Literal

from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel

from core.bus import InMemoryEventBus
from core.config import Settings
from core.context import ContextoApp
from core.db import make_engine
from core.loader import cargar_modulos
from core.scheduler import Programador, TrabajoNoEncontrado


class Health(BaseModel):
    """Estado de la API: versión de Trasno y módulos registrados."""

    status: Literal["ok"] = "ok"
    version: str
    modulos: list[str]


class TrabajoSalida(BaseModel):
    """Un trabajo programado y cuándo toca la próxima vez."""

    nombre: str
    proxima: datetime | None


@asynccontextmanager
async def _ciclo_de_vida(app: FastAPI) -> AsyncIterator[None]:
    """Arranca el programador al levantar la API y lo para al cerrarla."""
    programador: Programador = app.state.programador
    if getattr(app.state.ctx.settings, "scheduler_activo", True):
        programador.arrancar()
    try:
        yield
    finally:
        programador.parar()


def create_app(
    ctx: ContextoApp | None = None,
    paquete_modulos: str = "modules",
    extras: Sequence[str] = ("agent",),
) -> FastAPI:
    """Crea la app: registra los módulos en `ctx` y monta los routers que hayan añadido."""
    ctx = ctx or _contexto_por_defecto()
    modulos = cargar_modulos(ctx, paquete_modulos=paquete_modulos, extras=extras)

    app = FastAPI(title="Trasno", version=version("trasno"), lifespan=_ciclo_de_vida)
    app.state.ctx = ctx
    app.state.modulos = modulos
    app.state.programador = Programador(ctx.trabajos, ctx.settings.timezone)
    app.add_api_route("/health", health, methods=["GET"], response_model=Health)
    app.add_api_route("/jobs", listar_trabajos, methods=["GET"], response_model=list[TrabajoSalida])
    app.add_api_route("/jobs/{nombre}/run", ejecutar_trabajo, methods=["POST"], status_code=204)
    for router in ctx.routers:
        app.include_router(router)
    return app


def health(request: Request) -> Health:
    """Devuelve la versión y los módulos cargados."""
    return Health(version=request.app.version, modulos=request.app.state.modulos)


def listar_trabajos(request: Request) -> list[TrabajoSalida]:
    """Trabajos programados por los módulos y su próxima ejecución."""
    programador: Programador = request.app.state.programador
    return [
        TrabajoSalida(nombre=nombre, proxima=proxima)
        for nombre, proxima in programador.proximas(datetime.now(UTC)).items()
    ]


def ejecutar_trabajo(nombre: str, request: Request) -> None:
    """Ejecuta un trabajo ya, sin esperar a su hora (útil para probar el briefing)."""
    try:
        request.app.state.programador.ejecutar_ahora(nombre)
    except TrabajoNoEncontrado as error:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"No hay ningún trabajo {nombre!r}"
        ) from error


def _contexto_por_defecto() -> ContextoApp:
    return ContextoApp(bus=InMemoryEventBus(), engine_factory=make_engine, settings=Settings())
