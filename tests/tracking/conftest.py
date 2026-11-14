from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine

from core.db import make_engine
from core.migraciones import migrar_todo
from modules.tracking.application.casos_uso import CasosUsoTracking
from modules.tracking.application.ports import RepositorioEntradas, RepositorioMetricas
from modules.tracking.infrastructure.memoria import (
    RepositorioEntradasMemoria,
    RepositorioMetricasMemoria,
)
from modules.tracking.infrastructure.repositorios import (
    RepositorioEntradasSQL,
    RepositorioMetricasSQL,
)

USER_ID = 1

AHORA = datetime(2026, 11, 14, 9, 30, tzinfo=UTC)


@pytest.fixture
def engine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    """Engine de un tracking.sqlite temporal, creado con las migraciones reales."""
    monkeypatch.setenv("TRASNO_DATA_DIR", str(tmp_path))
    migrar_todo()
    engine = make_engine("tracking")
    yield engine
    engine.dispose()


@pytest.fixture(params=["memoria", "sql"])
def repos(request: pytest.FixtureRequest) -> tuple[RepositorioMetricas, RepositorioEntradas]:
    """Repositorios bajo prueba; los mismos tests corren contra cada implementación."""
    if request.param == "memoria":
        return RepositorioMetricasMemoria(), RepositorioEntradasMemoria()
    engine = request.getfixturevalue("engine")
    return RepositorioMetricasSQL(engine, USER_ID), RepositorioEntradasSQL(engine, USER_ID)


@pytest.fixture
def casos(repos: tuple[RepositorioMetricas, RepositorioEntradas]) -> CasosUsoTracking:
    metricas, entradas = repos
    return CasosUsoTracking(metricas, entradas, reloj=lambda: AHORA)
