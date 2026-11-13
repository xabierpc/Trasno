"""Entorno de Alembic para core.sqlite."""

from __future__ import annotations

from alembic import context
from sqlalchemy import Connection

from core.db import make_engine
from core.models import Base

target_metadata = Base.metadata


def _ejecutar(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,  # SQLite no soporta la mayoría de ALTER TABLE
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Migra sobre `core.sqlite`, o sobre la conexión que se pase en config.attributes."""
    connection = context.config.attributes.get("connection")
    if connection is not None:
        _ejecutar(connection)
        return
    engine = make_engine("core")
    try:
        with engine.connect() as conn:
            _ejecutar(conn)
    finally:
        engine.dispose()


if context.is_offline_mode():
    raise RuntimeError("Trasno no usa migraciones en modo offline")
run_migrations_online()
