from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import Engine

from core.db import make_engine
from core.migraciones import migrar_todo
from modules.planning.application.casos_uso import CasosUsoPlanning
from modules.planning.application.ports import (
    RepositorioBloques,
    RepositorioEventos,
    RepositorioTareas,
)
from modules.planning.infrastructure.memoria import (
    RepositorioBloquesMemoria,
    RepositorioEventosMemoria,
    RepositorioTareasMemoria,
)
from modules.planning.infrastructure.repositorios import (
    RepositorioBloquesSQL,
    RepositorioEventosSQL,
    RepositorioTareasSQL,
)

USER_ID = 1
ZONA = "Europe/Madrid"
MADRID = ZoneInfo(ZONA)
AHORA = datetime(2026, 11, 14, 9, 30, tzinfo=UTC)
LUNES = date(2026, 11, 16)

Repos = tuple[RepositorioTareas, RepositorioEventos, RepositorioBloques]


def a_las(hora: int, minuto: int = 0, dia: date = LUNES) -> datetime:
    """Instante en hora de Madrid: a_las(9, 30) es el lunes 16/11/2026 a las 9:30."""
    return datetime.combine(dia, time(hora, minuto), tzinfo=MADRID)


@pytest.fixture
def engine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    """Engine de un planning.sqlite temporal tal como lo deja `trasno migrate`."""
    monkeypatch.setenv("TRASNO_DATA_DIR", str(tmp_path))
    migrar_todo()
    engine = make_engine("planning")
    yield engine
    engine.dispose()


@pytest.fixture(params=["memoria", "sql"])
def repos(request: pytest.FixtureRequest) -> Repos:
    """Repositorios bajo prueba; los mismos tests corren contra cada implementación."""
    if request.param == "memoria":
        return RepositorioTareasMemoria(), RepositorioEventosMemoria(), RepositorioBloquesMemoria()
    engine = request.getfixturevalue("engine")
    return (
        RepositorioTareasSQL(engine, USER_ID),
        RepositorioEventosSQL(engine, USER_ID),
        RepositorioBloquesSQL(engine, USER_ID),
    )


@pytest.fixture
def casos(repos: Repos) -> CasosUsoPlanning:
    tareas, eventos, bloques = repos
    return CasosUsoPlanning(tareas, eventos, bloques, zona=ZONA, reloj=lambda: AHORA)
