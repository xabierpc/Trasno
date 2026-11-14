from __future__ import annotations

from datetime import UTC, datetime

import pytest

from modules.tracking.application.casos_uso import CasosUsoTracking
from modules.tracking.application.ports import RepositorioEntradas, RepositorioMetricas
from modules.tracking.infrastructure.memoria import (
    RepositorioEntradasMemoria,
    RepositorioMetricasMemoria,
)

AHORA = datetime(2026, 11, 14, 9, 30, tzinfo=UTC)


@pytest.fixture(params=["memoria"])
def repos(request: pytest.FixtureRequest) -> tuple[RepositorioMetricas, RepositorioEntradas]:
    """Repositorios bajo prueba; los mismos tests corren contra cada implementación."""
    return RepositorioMetricasMemoria(), RepositorioEntradasMemoria()


@pytest.fixture
def casos(repos: tuple[RepositorioMetricas, RepositorioEntradas]) -> CasosUsoTracking:
    metricas, entradas = repos
    return CasosUsoTracking(metricas, entradas, reloj=lambda: AHORA)
