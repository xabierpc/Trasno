"""Engines SQLite por módulo (implementa `core.contracts.make_engine`) y tipos compartidos."""

from __future__ import annotations

from datetime import UTC, datetime
from sqlite3 import Connection as SQLiteConnection
from typing import Any

from sqlalchemy import DateTime, Dialect, Engine, create_engine, event
from sqlalchemy.types import TypeDecorator

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


class TZDateTime(TypeDecorator[datetime]):
    """Datetime con zona: se guarda en UTC (SQLite no guarda zonas) y se lee como UTC aware."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("TZDateTime exige un datetime con zona horaria")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        return None if value is None else value.replace(tzinfo=UTC)
