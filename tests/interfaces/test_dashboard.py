from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
import streamlit as st
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from core.bus import InMemoryEventBus
from core.config import Settings
from core.context import ContextoApp
from core.db import make_engine
from interfaces.api.app import create_app
from interfaces.dashboard import cliente

APP = Path(__file__).resolve().parents[2] / "interfaces" / "dashboard" / "app.py"
PAQUETE = "modulos_dashboard_prueba"


@pytest.fixture(autouse=True)
def limpiar_cache() -> Iterator[None]:
    st.cache_resource.clear()
    yield
    st.cache_resource.clear()


@pytest.fixture
def api_con_modulo_falso(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """El dashboard habla con la API real (en memoria) que tiene un módulo `falso` cargado."""
    (tmp_path / PAQUETE / "falso").mkdir(parents=True)
    (tmp_path / PAQUETE / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / PAQUETE / "falso" / "__init__.py").write_text(
        "def register(ctx):\n    pass\n", encoding="utf-8"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    ctx = ContextoApp(
        bus=InMemoryEventBus(), engine_factory=make_engine, settings=Settings(_env_file=None)
    )
    api = create_app(ctx, paquete_modulos=PAQUETE, extras=())
    monkeypatch.setattr(cliente, "_crear_cliente", lambda: TestClient(api))
    yield
    for nombre in [n for n in sys.modules if n.split(".")[0] == PAQUETE]:
        del sys.modules[nombre]


@pytest.fixture
def api_caida(monkeypatch: pytest.MonkeyPatch) -> None:
    def rechazar(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("conexión rechazada", request=request)

    monkeypatch.setattr(
        cliente,
        "_crear_cliente",
        lambda: httpx.Client(base_url=cliente.API_URL, transport=httpx.MockTransport(rechazar)),
    )


@pytest.mark.usefixtures("api_con_modulo_falso")
def test_portada_muestra_estado_y_modulos() -> None:
    at = AppTest.from_file(str(APP)).run()

    assert not at.exception
    assert "0.1.0" in at.success[0].value
    assert any(f"{PAQUETE}.falso" in md.value for md in at.markdown)


@pytest.mark.usefixtures("api_caida")
def test_portada_avisa_si_la_api_no_responde() -> None:
    at = AppTest.from_file(str(APP)).run()

    assert not at.exception
    assert cliente.API_URL in at.error[0].value
