from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine

from core.db import make_engine
from core.migraciones import migrar_todo
from modules.training.application.casos_uso import CasosUsoTraining
from modules.training.application.ports import RepositorioSesiones
from modules.training.domain.sesiones import Ejercicio, Serie
from modules.training.infrastructure.memoria import RepositorioSesionesMemoria
from modules.training.infrastructure.repositorios import RepositorioSesionesSQL

USER_ID = 1
AHORA = datetime(2026, 11, 14, 19, 0, tzinfo=UTC)
D10, D12, D14 = date(2026, 11, 10), date(2026, 11, 12), date(2026, 11, 14)


@pytest.fixture
def engine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    """Engine de un training.sqlite temporal tal como lo deja `trasno migrate`."""
    monkeypatch.setenv("TRASNO_DATA_DIR", str(tmp_path))
    migrar_todo()
    engine = make_engine("training")
    yield engine
    engine.dispose()


@pytest.fixture(params=["memoria", "sql"])
def repo(request: pytest.FixtureRequest) -> RepositorioSesiones:
    """Repositorio bajo prueba; los mismos tests corren contra cada implementación."""
    if request.param == "memoria":
        return RepositorioSesionesMemoria()
    return RepositorioSesionesSQL(request.getfixturevalue("engine"), USER_ID)


@pytest.fixture
def casos(repo: RepositorioSesiones) -> CasosUsoTraining:
    return CasosUsoTraining(repo, reloj=lambda: AHORA)


def ejercicio(nombre: str, *series: tuple[int, float]) -> Ejercicio:
    """Atajo: ejercicio("press banca", (8, 60), (6, 65)) → reps y peso de cada serie."""
    return Ejercicio(nombre=nombre, series=tuple(Serie(reps=r, peso=p) for r, p in series))
