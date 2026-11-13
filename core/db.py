"""Engines SQLite por módulo: implementa `core.contracts.make_engine`."""

from __future__ import annotations

from sqlite3 import Connection as SQLiteConnection
from typing import Any

from sqlalchemy import Engine, create_engine, event

from core.config import Settings


def make_engine(module: str) -> Engine:
    """Crea el engine SQLite de `<data_dir>/<module>.sqlite` con foreign_keys=ON y WAL."""
    data_dir = Settings().data_dir
    data_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{data_dir / f'{module}.sqlite'}")
    event.listen(engine, "connect", _configurar_conexion)
    return engine


def _configurar_conexion(dbapi_connection: SQLiteConnection, _connection_record: Any) -> None:
    """Activa claves foráneas y WAL en cada conexión nueva del pool."""
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
    finally:
        cursor.close()
