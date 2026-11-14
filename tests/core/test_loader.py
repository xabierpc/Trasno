from __future__ import annotations

import logging
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from core.bus import InMemoryEventBus
from core.config import Settings
from core.context import ContextoApp
from core.db import make_engine
from core.loader import cargar_modulos

MODULO_FALSO = """
from fastapi import APIRouter


def register(ctx):
    ctx.add_router(APIRouter(prefix="/falso"))
"""


@pytest.fixture
def ctx() -> ContextoApp:
    return ContextoApp(
        bus=InMemoryEventBus(), engine_factory=make_engine, settings=Settings(_env_file=None)
    )


@pytest.fixture
def paquete_temporal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """Crea `modulos_prueba/` con un módulo que se registra y otro sin register."""
    raiz = tmp_path / "modulos_prueba"
    (raiz / "falso").mkdir(parents=True)
    (raiz / "sin_register").mkdir()
    (raiz / "__init__.py").write_text("", encoding="utf-8")
    (raiz / "falso" / "__init__.py").write_text(MODULO_FALSO, encoding="utf-8")
    (raiz / "sin_register" / "__init__.py").write_text("", encoding="utf-8")
    (raiz / "suelto.py").write_text("", encoding="utf-8")  # no es paquete: se ignora
    monkeypatch.syspath_prepend(str(tmp_path))
    yield "modulos_prueba"
    # Que el siguiente test importe su propia copia, no la cacheada de este.
    for nombre in [n for n in sys.modules if n.split(".")[0] == "modulos_prueba"]:
        del sys.modules[nombre]


def test_registra_un_modulo_nuevo_sin_tocar_el_core(
    ctx: ContextoApp, paquete_temporal: str
) -> None:
    registrados = cargar_modulos(ctx, paquete_modulos=paquete_temporal, extras=())

    assert registrados == ["modulos_prueba.falso"]
    assert [router.prefix for router in ctx.routers] == ["/falso"]


def test_modulo_sin_register_se_ignora_con_aviso(
    ctx: ContextoApp, paquete_temporal: str, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger="core.loader"):
        cargar_modulos(ctx, paquete_modulos=paquete_temporal, extras=())

    assert "modulos_prueba.sin_register" in caplog.text


def test_carga_los_modulos_reales_y_agent(
    ctx: ContextoApp,
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "TRASNO_DATA_DIR", str(tmp_path)
    )  # cada módulo abre su engine al registrarse
    with caplog.at_level(logging.WARNING, logger="core.loader"):
        registrados = cargar_modulos(ctx)

    assert registrados == ["modules.tracking", "modules.training"]
    for nombre in ("modules.analytics", "modules.planning", "agent"):
        assert nombre in caplog.text


def test_series_providers_devuelve_los_registrados_sin_exponer_la_lista(ctx: ContextoApp) -> None:
    proveedor = object()
    ctx.add_series_provider(proveedor)  # type: ignore[arg-type]

    vistos = ctx.series_providers()
    vistos.clear()

    assert ctx.series_providers() == [proveedor]
