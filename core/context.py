"""Contexto de la aplicación: implementa `core.contracts.AppContext`."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from fastapi import APIRouter
from sqlalchemy import Engine

from core.contracts import EventBus, SeriesProvider, Settings


@dataclass
class ContextoApp:
    """Lo que recibe cada módulo en `register(ctx)`; acumula sus routers y proveedores."""

    bus: EventBus
    engine_factory: Callable[[str], Engine]
    settings: Settings
    routers: list[APIRouter] = field(default_factory=list)
    series_providers: list[SeriesProvider] = field(default_factory=list)

    def add_router(self, router: APIRouter) -> None:
        """Guarda el router para que la app de FastAPI lo monte."""
        self.routers.append(router)

    def add_series_provider(self, provider: SeriesProvider) -> None:
        """Guarda el proveedor para que analytics lo consulte."""
        self.series_providers.append(provider)
