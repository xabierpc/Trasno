from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

import core
from core.db import make_engine
from core.models import AgentLog, Base, User

ALEMBIC_INI = Path(core.__file__).parent / "migrations" / "alembic.ini"


@pytest.fixture
def engine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    monkeypatch.setenv("TRASNO_DATA_DIR", str(tmp_path))
    command.upgrade(Config(str(ALEMBIC_INI)), "head")
    engine = make_engine("core")
    yield engine
    engine.dispose()


def test_upgrade_head_deja_un_usuario(engine: Engine) -> None:
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(User)) == 1


def test_modelos_coinciden_con_migraciones(engine: Engine) -> None:
    with engine.connect() as conn:
        diferencias = compare_metadata(MigrationContext.configure(conn), Base.metadata)

    assert diferencias == []


def test_agent_log_conserva_el_instante_con_zona(engine: Engine) -> None:
    momento = datetime(2026, 11, 14, 1, 30, tzinfo=ZoneInfo("Europe/Madrid"))

    with Session(engine) as session:
        session.add(
            AgentLog(
                user_id=1,
                herramienta="registrar_metrica",
                argumentos={"nombre": "peso", "valor": 72.5},
                resultado="ok",
                timestamp=momento,
            )
        )
        session.commit()
        guardado = session.scalars(select(AgentLog)).one()

        assert guardado.timestamp == momento
        assert guardado.timestamp.tzinfo == UTC
        assert guardado.argumentos == {"nombre": "peso", "valor": 72.5}
