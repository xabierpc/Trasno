"""Migraciones de Trasno: Alembic del core y de cada módulo, cada uno sobre su propio .sqlite.

Convenciones de un módulo `modules/<m>/`:
- `infrastructure/migrations/env.py` (+ `versions/`): su Alembic. El env.py solo necesita
  `ejecutar_env(Base.metadata, "<m>")`.
- `infrastructure/arranque.py` con `datos_arranque(engine) -> None` (opcional): se ejecuta
  tras migrar, en cada `trasno migrate`, así que debe ser idempotente.
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
from dataclasses import dataclass
from pathlib import Path

from alembic import command, context
from alembic.config import Config
from sqlalchemy import Connection, MetaData

from core.db import make_engine
from core.loader import subpaquetes

logger = logging.getLogger(__name__)

MIGRACIONES_CORE = Path(__file__).parent / "migrations"


@dataclass(frozen=True)
class _Modulo:
    paquete: str  # p. ej. "modules.tracking"
    directorio: Path

    @property
    def nombre(self) -> str:
        """Nombre corto, que es también el de su .sqlite."""
        return self.paquete.rsplit(".", 1)[-1]

    @property
    def migraciones(self) -> Path:
        return self.directorio / "infrastructure" / "migrations"

    @property
    def tiene_migraciones(self) -> bool:
        return (self.migraciones / "env.py").is_file()

    @property
    def tiene_datos_arranque(self) -> bool:
        return (self.directorio / "infrastructure" / "arranque.py").is_file()


def migrar_todo(paquete_modulos: str = "modules") -> list[str]:
    """Migra core y cada módulo a head; después aplica sus datos de arranque."""
    modulos = [_Modulo(nombre, _directorio(nombre)) for nombre in subpaquetes(paquete_modulos)]

    _upgrade("core", MIGRACIONES_CORE)
    migrados = ["core"]
    for modulo in modulos:
        if modulo.tiene_migraciones:
            _upgrade(modulo.nombre, modulo.migraciones)
            migrados.append(modulo.nombre)

    for modulo in modulos:
        if modulo.tiene_datos_arranque:
            _datos_arranque(modulo)
    return migrados


def ejecutar_env(target_metadata: MetaData, modulo: str) -> None:
    """Cuerpo común de los env.py: migra la conexión recibida o, si no hay, `<modulo>.sqlite`."""
    if context.is_offline_mode():
        raise RuntimeError("Trasno no usa migraciones en modo offline")
    connection = context.config.attributes.get("connection")
    if connection is not None:
        _ejecutar(connection, target_metadata)
        return
    engine = make_engine(modulo)
    try:
        with engine.begin() as conn:
            _ejecutar(conn, target_metadata)
    finally:
        engine.dispose()


def _ejecutar(connection: Connection, target_metadata: MetaData) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,  # SQLite no soporta la mayoría de ALTER TABLE
    )
    with context.begin_transaction():
        context.run_migrations()


def _upgrade(nombre: str, migraciones: Path) -> None:
    config = Config()
    config.set_main_option("script_location", str(migraciones))
    engine = make_engine(nombre)
    try:
        with engine.begin() as conn:
            config.attributes["connection"] = conn
            command.upgrade(config, "head")
    finally:
        engine.dispose()
    logger.info("Migrado %s", nombre)


def _datos_arranque(modulo: _Modulo) -> None:
    arranque = importlib.import_module(f"{modulo.paquete}.infrastructure.arranque")
    engine = make_engine(modulo.nombre)
    try:
        arranque.datos_arranque(engine)
    finally:
        engine.dispose()
    logger.info("Datos de arranque de %s aplicados", modulo.nombre)


def _directorio(paquete: str) -> Path:
    spec = importlib.util.find_spec(paquete)
    if spec is None or not spec.submodule_search_locations:
        raise ModuleNotFoundError(paquete)
    return Path(next(iter(spec.submodule_search_locations)))
