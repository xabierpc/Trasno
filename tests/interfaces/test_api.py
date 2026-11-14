from __future__ import annotations

import runpy
import sys
from collections.abc import Iterator
from importlib.metadata import version
from pathlib import Path
from typing import Any

import pytest
import uvicorn
from fastapi.testclient import TestClient

from core.bus import InMemoryEventBus
from core.config import Settings
from core.context import ContextoApp
from core.db import make_engine
from interfaces.api.app import create_app

RAIZ_REPO = Path(__file__).resolve().parents[2]
PAQUETE = "modulos_api_prueba"

MODULO_FALSO = """
from fastapi import APIRouter

router = APIRouter(prefix="/falso")


@router.get("/ping")
def ping() -> dict[str, bool]:
    return {"pong": True}


def register(ctx):
    ctx.add_router(router)
"""


@pytest.fixture
def paquete_falso(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """Crea un paquete de módulos temporal con un único módulo `falso` que expone un router."""
    (tmp_path / PAQUETE / "falso").mkdir(parents=True)
    (tmp_path / PAQUETE / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / PAQUETE / "falso" / "__init__.py").write_text(MODULO_FALSO, encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    yield PAQUETE
    for nombre in [n for n in sys.modules if n.split(".")[0] == PAQUETE]:
        del sys.modules[nombre]


@pytest.fixture
def client(paquete_falso: str) -> TestClient:
    ctx = ContextoApp(
        bus=InMemoryEventBus(), engine_factory=make_engine, settings=Settings(_env_file=None)
    )
    return TestClient(create_app(ctx, paquete_modulos=paquete_falso, extras=()))


def test_health_devuelve_version_y_modulos(client: TestClient) -> None:
    respuesta = client.get("/health")

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "status": "ok",
        "version": version("trasno"),
        "modulos": [f"{PAQUETE}.falso"],
    }


def test_monta_el_router_del_modulo_falso(client: TestClient) -> None:
    respuesta = client.get("/falso/ping")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"pong": True}


def test_main_escucha_solo_en_localhost(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("TRASNO_DATA_DIR", str(tmp_path))  # main carga los módulos reales
    llamada: dict[str, Any] = {}
    monkeypatch.setattr(uvicorn, "run", lambda app, **kwargs: llamada.update(kwargs))

    runpy.run_path(str(RAIZ_REPO / "main.py"), run_name="__main__")

    assert llamada["host"] == "127.0.0.1"
