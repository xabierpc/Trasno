from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import streamlit as st
from fastapi import FastAPI
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from core.config import Settings
from interfaces.dashboard import cliente
from interfaces.dashboard.graficas import grafica_con_media_movil
from modules.tracking.api import crear_router
from modules.tracking.application.casos_uso import CasosUsoTracking
from modules.tracking.domain.metricas import Agregacion, TipoMetrica
from modules.tracking.infrastructure.memoria import (
    RepositorioEntradasMemoria,
    RepositorioMetricasMemoria,
)

PAGINA = Path(__file__).resolve().parents[2] / "interfaces" / "dashboard" / "pages" / "1_Peso.py"
MADRID = ZoneInfo("Europe/Madrid")
DE_DIA = datetime(2026, 11, 14, 9, 0, tzinfo=MADRID)
DE_MADRUGADA = datetime(2026, 11, 14, 1, 30, tzinfo=MADRID)
AYER, HOY = date(2026, 11, 13), date(2026, 11, 14)


@pytest.fixture(autouse=True)
def limpiar_cache() -> Iterator[None]:
    st.cache_resource.clear()
    yield
    st.cache_resource.clear()


@pytest.fixture
def casos() -> CasosUsoTracking:
    casos = CasosUsoTracking(RepositorioMetricasMemoria(), RepositorioEntradasMemoria())
    casos.crear_metrica("peso", "kg", TipoMetrica.NUMERICA, agregacion=Agregacion.MEDIA)
    return casos


@pytest.fixture
def abrir(
    casos: CasosUsoTracking, monkeypatch: pytest.MonkeyPatch
) -> Callable[[datetime], AppTest]:
    """Abre la página contra una API de tracking en memoria con el reloj fijado."""

    def _abrir(ahora: datetime) -> AppTest:
        api = FastAPI()
        api.include_router(crear_router(casos, Settings(_env_file=None), reloj=lambda: ahora))
        monkeypatch.setattr(cliente, "_crear_cliente", lambda: TestClient(api))
        return AppTest.from_file(str(PAGINA)).run()

    return _abrir


def valores(casos: CasosUsoTracking) -> list[tuple[date, object]]:
    return [(e.logical_date, e.valor) for e in casos.listar_entradas("peso", date.min, date.max)]


def test_sin_datos_avisa_y_no_pinta_grafica(abrir: Callable[[datetime], AppTest]) -> None:
    at = abrir(DE_DIA)

    assert not at.exception
    assert "Todavía no hay pesos" in at.info[0].value
    assert not at.get("plotly_chart")


def test_registrar_un_peso_aparece_en_la_grafica(
    abrir: Callable[[datetime], AppTest], casos: CasosUsoTracking
) -> None:
    at = abrir(DE_DIA)
    assert at.date_input[0].value == HOY and not at.radio

    at.number_input[0].set_value(74.3)
    at.button[0].click().run()

    assert not at.exception
    assert "74.3" in at.success[0].value
    assert valores(casos) == [(HOY, 74.3)]
    (grafica,) = at.get("plotly_chart")
    trazas = json.loads(grafica.proto.spec)["data"]
    assert [t["name"] for t in trazas] == ["Peso", "Media 7 días"]


def test_de_madrugada_pregunta_ayer_u_hoy(
    abrir: Callable[[datetime], AppTest], casos: CasosUsoTracking
) -> None:
    at = abrir(DE_MADRUGADA)
    assert at.radio[0].options == ["Ayer (13/11)", "Hoy (14/11)"] and not at.date_input

    at.number_input[0].set_value(75.0)
    at.radio[0].set_value(AYER)
    at.button[0].click().run()

    assert valores(casos) == [(AYER, 75.0)]


def test_guardar_sin_valor_avisa_y_no_registra(
    abrir: Callable[[datetime], AppTest], casos: CasosUsoTracking
) -> None:
    at = abrir(DE_DIA)

    at.button[0].click().run()

    assert "Escribe un peso" in at.warning[0].value
    assert valores(casos) == []


def test_la_media_movil_usa_solo_los_siete_dias_anteriores() -> None:
    puntos = [(date(2026, 11, 9), 76.0), (date(2026, 11, 1), 80.0), (date(2026, 11, 8), 78.0)]

    figura = grafica_con_media_movil(puntos, "Peso", "kg")

    assert list(figura.data[0].y) == [80.0, 78.0, 76.0]
    assert list(figura.data[1].y) == [80.0, 78.0, 77.0]
