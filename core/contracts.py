"""Contratos compartidos entre el core y los módulos.

Solo firmas y docstrings: las implementaciones viven en otros ficheros de `core/`.
Cambiar este fichero requiere un PR propio aprobado por el otro desarrollador.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, time
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, TypeVar, runtime_checkable

if TYPE_CHECKING:
    from fastapi import APIRouter
    from sqlalchemy import Engine


class Settings(Protocol):
    """Configuración global de la aplicación; la implementa `core.config.Settings`."""

    data_dir: Path
    user_id: int
    ventana_madrugada: tuple[time, time]
    backup_dir: Path
    backup_retencion_dias: int
    timezone: str


def make_engine(module: str) -> Engine:
    """Crea el engine SQLite de `data/<module>.sqlite` con foreign_keys=ON y WAL."""
    ...


@dataclass(frozen=True, kw_only=True)
class Event:
    """Clase base de los eventos de dominio que viajan por el EventBus."""


E = TypeVar("E", bound=Event)


class EventBus(Protocol):
    """Bus de eventos en proceso: los módulos se comunican sin importarse entre sí."""

    def publish(self, event: Event) -> None:
        """Entrega el evento a todos los suscriptores de su tipo."""
        ...

    def subscribe(self, event_type: type[E], handler: Callable[[E], None]) -> None:
        """Registra `handler` para los eventos de tipo `event_type`."""
        ...


@dataclass(frozen=True)
class SeriesInfo:
    """Descripción de una serie temporal que un módulo expone a analytics."""

    nombre: str
    unidad: str
    descripcion: str = ""


@runtime_checkable
class SeriesProvider(Protocol):
    """Fuente de series temporales; analytics lee los datos solo a través de esto."""

    def list_series(self) -> list[SeriesInfo]:
        """Devuelve las series que ofrece el proveedor."""
        ...

    def get_series(self, nombre: str, desde: date, hasta: date) -> list[tuple[date, float]]:
        """Devuelve los puntos (fecha lógica, valor) de la serie entre `desde` y `hasta`."""
        ...


class AppContext(Protocol):
    """Lo que el core ofrece a cada módulo en `register(ctx)`."""

    bus: EventBus
    engine_factory: Callable[[str], Engine]
    settings: Settings

    def add_router(self, router: APIRouter) -> None:
        """Monta el router FastAPI del módulo en la API."""
        ...

    def add_series_provider(self, provider: SeriesProvider) -> None:
        """Registra un proveedor de series para analytics."""
        ...
