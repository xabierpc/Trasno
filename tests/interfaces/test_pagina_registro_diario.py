from __future__ import annotations

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
from modules.tracking.api import crear_router
from modules.tracking.application.casos_uso import CasosUsoTracking
from modules.tracking.domain.metricas import Agregacion, PoliticaDuplicado, TipoMetrica
from modules.tracking.infrastructure.memoria import (
    RepositorioEntradasMemoria,
    RepositorioMetricasMemoria,
)

PAGINA = (
    Path(__file__).resolve().parents[2]
    / "interfaces"
    / "dashboard"
    / "pages"
    / "2_Registro_diario.py"
)
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
    """Una métrica de cada tipo, como las que deja `trasno migrate`."""
    casos = CasosUsoTracking(RepositorioMetricasMemoria(), RepositorioEntradasMemoria())
    casos.crear_metrica("peso", "kg", TipoMetrica.NUMERICA, agregacion=Agregacion.MEDIA)
    casos.crear_metrica("pasos", "pasos", TipoMetrica.CONTEO, Agregacion.SUMA, objetivo=8000)
    casos.crear_metrica("sueño", "min", TipoMetrica.DURACION, objetivo=420)
    casos.crear_metrica("ánimo", "1-10", TipoMetrica.ESCALA, escala_max=10)
    casos.crear_metrica("ocio", "", TipoMetrica.CATEGORICA, categorias=("leer", "jugar"))
    casos.crear_metrica("leer", "", TipoMetrica.BOOLEANA)
    casos.crear_metrica("meditar", "", TipoMetrica.BOOLEANA)
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


def del_dia(casos: CasosUsoTracking, dia: date) -> dict[str, object]:
    return {
        m.nombre: e.valor
        for m in casos.listar_metricas()
        for e in casos.listar_entradas(m.nombre, dia, dia)
    }


def guardar(at: AppTest) -> AppTest:
    return at.button[0].click().run()


def test_muestra_un_campo_por_metrica_activa(abrir: Callable[[datetime], AppTest]) -> None:
    at = abrir(DE_DIA)

    assert not at.exception
    assert [n.label for n in at.number_input] == [
        "Pasos (pasos)",
        "Peso (kg)",
        "Sueño (horas)",
        "Ánimo (1-10)",
    ]
    assert [s.label for s in at.selectbox] == ["Ocio"]
    assert [c.label for c in at.checkbox[:2]] == ["Leer", "Meditar"]
    assert all(n.value is None for n in at.number_input)


def test_guarda_cada_tipo_con_su_valor_y_deja_fuera_lo_vacio(
    abrir: Callable[[datetime], AppTest], casos: CasosUsoTracking
) -> None:
    at = abrir(DE_DIA)

    at.number_input(key=f"pasos-{HOY}").set_value(9000)
    at.number_input(key=f"sueño-{HOY}").set_value(7.5)
    at.number_input(key=f"ánimo-{HOY}").set_value(8)
    at.selectbox(key=f"ocio-{HOY}").set_value("jugar")
    at.checkbox(key=f"leer-{HOY}").check()
    guardar(at)

    assert not at.exception and not at.error
    assert del_dia(casos, HOY) == {
        "pasos": 9000,
        "sueño": 450,
        "ánimo": 8,
        "ocio": "jugar",
        "leer": True,
    }
    assert "pasos" in at.success[0].value and "peso" not in at.success[0].value


def test_arranca_con_lo_ya_registrado_y_solo_envia_los_cambios(
    abrir: Callable[[datetime], AppTest], casos: CasosUsoTracking
) -> None:
    casos.registrar_metrica("peso", 74.3, HOY)
    casos.registrar_metrica("sueño", 420, HOY)
    casos.registrar_metrica("leer", True, HOY)
    eventos: list[str] = []
    casos._al_registrar = lambda definicion, _entrada: eventos.append(definicion.nombre)
    at = abrir(DE_DIA)
    assert at.number_input(key=f"peso-{HOY}").value == 74.3
    assert at.number_input(key=f"sueño-{HOY}").value == 7.0
    assert at.checkbox(key=f"leer-{HOY}").value is True

    guardar(at)
    assert "nada nuevo" in at.warning[0].value and eventos == []

    at.number_input(key=f"peso-{HOY}").set_value(74.0)
    at.checkbox(key=f"leer-{HOY}").uncheck()
    guardar(at)

    assert eventos == ["leer", "peso"]  # en el orden alfabético de las métricas
    assert del_dia(casos, HOY) == {"peso": 74.0, "sueño": 420, "leer": False}


def test_una_metrica_keep_all_acumula_en_vez_de_rellenarse(
    abrir: Callable[[datetime], AppTest], casos: CasosUsoTracking
) -> None:
    casos.crear_metrica(
        "cafés", "tazas", TipoMetrica.CONTEO, Agregacion.SUMA, PoliticaDuplicado.KEEP_ALL
    )
    casos.registrar_metrica("cafés", 1, HOY)
    at = abrir(DE_DIA)
    assert at.number_input(key=f"cafés-{HOY}").value is None

    at.number_input(key=f"cafés-{HOY}").set_value(1)
    guardar(at)

    assert [e.valor for e in casos.listar_entradas("cafés", HOY, HOY)] == [1, 1]


def test_de_madrugada_pregunta_ayer_u_hoy(
    abrir: Callable[[datetime], AppTest], casos: CasosUsoTracking
) -> None:
    at = abrir(DE_MADRUGADA)
    assert at.radio[0].options == ["Ayer (13/11)", "Hoy (14/11)"] and not at.date_input

    at.checkbox(key=f"meditar-{AYER}").check()
    guardar(at)

    assert del_dia(casos, AYER) == {"meditar": True} and del_dia(casos, HOY) == {}


def test_muestra_las_rachas_de_habitos_y_metricas_con_objetivo(
    abrir: Callable[[datetime], AppTest], casos: CasosUsoTracking
) -> None:
    for dia in (date(2026, 11, 11), date(2026, 11, 12), AYER):
        casos.registrar_metrica("leer", True, dia)
    casos.registrar_metrica("pasos", 9000, AYER)

    at = abrir(DE_DIA)

    filas = at.dataframe[0].value
    assert list(filas["Métrica"]) == ["Leer", "Meditar", "Pasos", "Sueño"]
    leer = filas[filas["Métrica"] == "Leer"].iloc[0]
    assert (leer["Racha"], leer["Máxima"], leer["7 días"], leer["30 días"]) == (3, 3, "3/7", "3/30")
    assert filas[filas["Métrica"] == "Pasos"].iloc[0]["Racha"] == 1


def test_desactivar_una_metrica_la_quita_del_formulario(
    abrir: Callable[[datetime], AppTest], casos: CasosUsoTracking
) -> None:
    at = abrir(DE_DIA)

    at.checkbox(key="activa-peso").uncheck().run()

    assert not at.exception
    assert "Peso (kg)" not in [n.label for n in at.number_input]
    assert [m.nombre for m in casos.listar_metricas() if not m.activa] == ["peso"]
    assert at.checkbox(key="activa-peso").value is False
