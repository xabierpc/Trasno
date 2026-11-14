"""Descubrimiento de módulos: importa cada paquete y llama a su `register(ctx)`."""

from __future__ import annotations

import importlib
import logging
import pkgutil
from collections.abc import Sequence

from core.contracts import AppContext

logger = logging.getLogger(__name__)


def cargar_modulos(
    ctx: AppContext,
    paquete_modulos: str = "modules",
    extras: Sequence[str] = ("agent",),
) -> list[str]:
    """Registra los subpaquetes de `paquete_modulos` y los `extras`; devuelve los registrados."""
    nombres = [*subpaquetes(paquete_modulos), *extras]
    return [nombre for nombre in nombres if _registrar(ctx, nombre)]


def subpaquetes(paquete: str) -> list[str]:
    """Nombres completos de los subpaquetes directos de `paquete`, en orden alfabético."""
    raiz = importlib.import_module(paquete)
    return sorted(
        f"{paquete}.{info.name}" for info in pkgutil.iter_modules(raiz.__path__) if info.ispkg
    )


def _registrar(ctx: AppContext, nombre: str) -> bool:
    """Importa `nombre` y llama a su `register(ctx)`; avisa y devuelve False si no lo tiene."""
    modulo = importlib.import_module(nombre)
    register = getattr(modulo, "register", None)
    if not callable(register):
        logger.warning("El módulo %s no define register(ctx); se ignora", nombre)
        return False
    register(ctx)
    logger.info("Módulo %s registrado", nombre)
    return True
