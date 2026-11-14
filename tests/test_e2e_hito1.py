"""Cierre de las fases 0-1: los cinco puntos del plan, de extremo a extremo.

Todo corre sobre un data_dir temporal con las piezas reales: `trasno migrate`, la app de
FastAPI con los módulos descubiertos por el loader, la página de Streamlit y el backup.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest
import streamlit as st
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from core.cli import main
from interfaces.api.app import create_app
from interfaces.dashboard import cliente
from modules.analytics.application.series import CatalogoSeries

PAGINA_PESO = (
    Path(__file__).resolve().parents[1] / "interfaces" / "dashboard" / "pages" / "1_Peso.py"
)


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    data = tmp_path / "data"
    monkeypatch.setenv("TRASNO_DATA_DIR", str(data))
    monkeypatch.setenv("TRASNO_BACKUP_DIR", str(tmp_path / "backups"))
    assert main(["migrate"]) == 0
    return data


@pytest.fixture
def api(data_dir: Path) -> Iterator[TestClient]:
    st.cache_resource.clear()
    with TestClient(create_app()) as client:
        yield client
    st.cache_resource.clear()


def registrar_peso(api: TestClient, valor: float, dia: str) -> None:
    cuerpo = {"metric": "peso", "valor": valor, "logical_date": dia}
    assert api.post("/tracking/entries", json=cuerpo).status_code == 201


def test_1_migrate_crea_core_y_tracking(data_dir: Path) -> None:
    assert (data_dir / "core.sqlite").is_file()
    assert (data_dir / "tracking.sqlite").is_file()


def test_2_dos_pesos_el_mismo_dia_dejan_uno(api: TestClient) -> None:
    registrar_peso(api, 74.3, "2026-11-14")
    registrar_peso(api, 74.0, "2026-11-14")

    entradas = api.get("/tracking/entries", params={"metric": "peso"}).json()

    assert [e["valor"] for e in entradas] == [74.0]


def test_3_la_pagina_muestra_el_valor_y_la_media_movil(
    api: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    fecha = api.get("/tracking/fecha-logica").json()
    # De madrugada la página pregunta y propone «ayer»; de día usa hoy.
    esperada = fecha["ayer"] if fecha["es_madrugada"] else fecha["hoy"]
    monkeypatch.setattr(cliente, "_crear_cliente", lambda: api)
    at = AppTest.from_file(str(PAGINA_PESO)).run()

    at.number_input[0].set_value(74.3)
    at.button[0].click().run()

    assert not at.exception
    entradas = api.get("/tracking/entries", params={"metric": "peso"}).json()
    assert [(e["logical_date"], e["valor"]) for e in entradas] == [(esperada, 74.3)]
    (grafica,) = at.get("plotly_chart")
    assert [t["name"] for t in json.loads(grafica.proto.spec)["data"]] == ["Peso", "Media 7 días"]


def test_4_backup_copia_los_dos_ficheros(
    api: TestClient, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    registrar_peso(api, 74.3, "2026-11-14")

    assert main(["backup"]) == 0

    (carpeta,) = (tmp_path / "backups").iterdir()
    assert sorted(f.name for f in carpeta.iterdir()) == ["core.sqlite", "tracking.sqlite"]
    assert "tracking.sqlite" in capsys.readouterr().out


def test_5_analytics_devuelve_la_serie_peso(api: TestClient) -> None:
    registrar_peso(api, 75.0, "2026-11-13")
    registrar_peso(api, 74.3, "2026-11-14")
    catalogo = CatalogoSeries(api.app.state.ctx.series_providers)

    assert "peso" in [s.nombre for s in catalogo.listar()]
    puntos = catalogo.obtener("peso", date(2026, 11, 1), date(2026, 11, 30))
    assert puntos == [(date(2026, 11, 13), 75.0), (date(2026, 11, 14), 74.3)]
