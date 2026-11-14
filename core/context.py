"""Contexto de la aplicación: implementa `core.contracts.AppContext`."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from fastapi import APIRouter
from sqlalchemy import Engine

from core.acciones import RegistroAccionesSQL
from core.contracts import (
    Disparador,
    EventBus,
    RegistroAcciones,
    SeccionBriefing,
    SeriesProvider,
    Settings,
    Tool,
)
from core.herramientas import HerramientaInvalida, validar
from core.scheduler import Trabajo


@dataclass
class ContextoApp:
    """Lo que recibe cada módulo en `register(ctx)`; acumula routers, proveedores y trabajos."""

    bus: EventBus
    engine_factory: Callable[[str], Engine]
    settings: Settings
    routers: list[APIRouter] = field(default_factory=list)
    proveedores_series: list[SeriesProvider] = field(default_factory=list)
    trabajos: list[Trabajo] = field(default_factory=list)
    secciones_briefing: list[SeccionBriefing] = field(default_factory=list)
    herramientas: dict[str, Tool] = field(default_factory=dict)
    _acciones: RegistroAcciones | None = field(default=None, repr=False)

    @property
    def acciones(self) -> RegistroAcciones:
        """Log del agente en `core.sqlite`; se abre la primera vez que se usa."""
        if self._acciones is None:
            self._acciones = RegistroAccionesSQL(self.engine_factory("core"), self.settings.user_id)
        return self._acciones

    def add_router(self, router: APIRouter) -> None:
        """Guarda el router para que la app de FastAPI lo monte."""
        self.routers.append(router)

    def add_series_provider(self, provider: SeriesProvider) -> None:
        """Guarda el proveedor para que analytics lo consulte."""
        self.proveedores_series.append(provider)

    def series_providers(self) -> list[SeriesProvider]:
        """Copia de los proveedores registrados: quien la recibe no altera el registro."""
        return list(self.proveedores_series)

    def add_briefing_section(self, seccion: SeccionBriefing) -> None:
        """Guarda la sección para que el briefing la incluya."""
        self.secciones_briefing.append(seccion)

    def briefing_sections(self) -> list[SeccionBriefing]:
        """Copia de las secciones registradas: quien la recibe no altera el registro."""
        return list(self.secciones_briefing)

    def add_tool(self, tool: Tool) -> None:
        """Valida la herramienta y la guarda para el agente."""
        if tool.nombre in self.herramientas:
            raise HerramientaInvalida(f"Hay dos herramientas llamadas {tool.nombre!r}")
        self.herramientas[tool.nombre] = validar(tool)

    def tools(self) -> list[Tool]:
        """Herramientas registradas, por nombre."""
        return sorted(self.herramientas.values(), key=lambda t: t.nombre)

    def add_job(self, nombre: str, tarea: Callable[[], None], cuando: Disparador) -> None:
        """Guarda el trabajo para que el programador lo ejecute cuando arranque la API."""
        self.trabajos.append(Trabajo(nombre=nombre, tarea=tarea, cuando=cuando))
