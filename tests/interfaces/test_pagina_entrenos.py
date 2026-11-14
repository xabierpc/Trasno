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
from interfaces.dashboard.entrenos import FilaEntreno, ejercicios_de_filas, resumen_ejercicio
from interfaces.dashboard.graficas import grafica_progreso_1rm, grafica_volumen_semanal
from modules.tracking.api import crear_router as router_tracking
from modules.tracking.application.casos_uso import CasosUsoTracking
from modules.tracking.infrastructure.memoria import (
    RepositorioEntradasMemoria,
    RepositorioMetricasMemoria,
)
from modules.training.api import crear_router as router_training
from modules.training.application.casos_uso import CasosUsoTraining
from modules.training.domain.sesiones import Ejercicio, Serie
from modules.training.infrastructure.memoria import RepositorioSesionesMemoria

PAGINA = (
    Path(__file__).resolve().parents[2] / "interfaces" / "dashboard" / "pages" / "3_Entrenos.py"
)
MADRID = ZoneInfo("Europe/Madrid")
DE_DIA = datetime(2026, 11, 14, 19, 0, tzinfo=MADRID)
DE_MADRUGADA = datetime(2026, 11, 14, 0, 30, tzinfo=MADRID)
AYER, HOY = date(2026, 11, 13), date(2026, 11, 14)


@pytest.fixture(autouse=True)
def limpiar_cache() -> Iterator[None]:
    st.cache_resource.clear()
    yield
    st.cache_resource.clear()


@pytest.fixture
def casos() -> CasosUsoTraining:
    return CasosUsoTraining(RepositorioSesionesMemoria())


@pytest.fixture
def abrir(
    casos: CasosUsoTraining, monkeypatch: pytest.MonkeyPatch
) -> Callable[[datetime], AppTest]:
    """Abre la página contra una API en memoria (training + fecha lógica de tracking)."""

    def _abrir(ahora: datetime) -> AppTest:
        tracking = CasosUsoTracking(RepositorioMetricasMemoria(), RepositorioEntradasMemoria())
        api = FastAPI()
        api.include_router(router_tracking(tracking, Settings(_env_file=None), reloj=lambda: ahora))
        api.include_router(router_training(casos))
        monkeypatch.setattr(cliente, "_crear_cliente", lambda: TestClient(api))
        return AppTest.from_file(str(PAGINA)).run()

    return _abrir


def banca(reps: int, peso: float, series: int = 1) -> Ejercicio:
    return Ejercicio(nombre="press banca", series=(Serie(reps=reps, peso=peso),) * series)


def guardar(at: AppTest) -> AppTest:
    return at.button(key="guardar_sesion").click().run()


def nombres_de_trazas(at: AppTest) -> list[str]:
    return [t["name"] for g in at.get("plotly_chart") for t in json.loads(g.proto.spec)["data"]]


# --- Página --------------------------------------------------------------------------------


def test_sin_datos_muestra_el_formulario_y_avisa(abrir: Callable[[datetime], AppTest]) -> None:
    at = abrir(DE_DIA)

    assert not at.exception
    assert at.date_input[0].value == HOY
    assert at.text_input(key="tipo-0").value == "fuerza"
    assert len([s for s in at.selectbox if s.label == "Ejercicio"]) == 4
    assert "no hay ejercicios" in at.info[0].value
    assert not at.get("plotly_chart")


def test_registrar_una_sesion_en_una_fila_y_ver_las_graficas(
    abrir: Callable[[datetime], AppTest], casos: CasosUsoTraining
) -> None:
    casos.registrar_sesion(date(2026, 11, 10), "fuerza", [banca(8, 60, series=3)])
    at = abrir(DE_DIA)

    at.number_input(key="duracion-0").set_value(50)
    at.number_input(key="energia-0").set_value(7)
    at.selectbox(key="ejercicio-0-0").set_value("press banca")
    at.number_input(key="reps-0-0").set_value(8)
    at.number_input(key="peso-0-0").set_value(62.5)
    guardar(at)

    assert not at.exception and not at.error
    _anterior, nueva = casos.listar_sesiones(date.min, date.max)
    assert (nueva.logical_date, nueva.tipo, nueva.duracion_min, nueva.energia_previa) == (
        HOY,
        "fuerza",
        50,
        7,
    )
    assert nueva.ejercicios == (banca(8, 62.5, series=3),)
    assert "1500 kg" in at.success[0].value
    assert any("récord de peso en press banca: 62.5 kg (antes 60)" in i.value for i in at.info)
    # El formulario queda vacío para la siguiente sesión
    assert at.selectbox(key="ejercicio-1-0").value is None
    assert at.number_input(key="reps-1-0").value is None
    assert nombres_de_trazas(at) == ["1RM press banca", "Volumen semanal"]
    assert list(at.dataframe[0].value["Ejercicios"]) == [
        "press banca 3x8x62.5",
        "press banca 3x8x60",
    ]


def test_una_sesion_de_cardio_no_necesita_ejercicios(
    abrir: Callable[[datetime], AppTest], casos: CasosUsoTraining
) -> None:
    at = abrir(DE_DIA)

    at.text_input(key="tipo-0").set_value("correr")
    at.number_input(key="duracion-0").set_value(30)
    guardar(at)

    (sesion,) = casos.listar_sesiones(date.min, date.max)
    assert (sesion.tipo, sesion.duracion_min, sesion.ejercicios) == ("correr", 30, ())


def test_una_fila_a_medias_avisa_y_no_guarda(
    abrir: Callable[[datetime], AppTest], casos: CasosUsoTraining
) -> None:
    casos.registrar_sesion(date(2026, 11, 10), "fuerza", [banca(8, 60)])
    at = abrir(DE_DIA)

    at.selectbox(key="ejercicio-0-0").set_value("press banca")
    guardar(at)

    assert "Fila 1: faltan las repeticiones" in at.warning[0].value
    assert len(casos.listar_sesiones(date.min, date.max)) == 1
    assert at.selectbox(key="ejercicio-0-0").value == "press banca"  # no se pierde lo escrito


def test_un_error_de_la_api_se_muestra(
    abrir: Callable[[datetime], AppTest], casos: CasosUsoTraining
) -> None:
    at = abrir(DE_DIA)

    at.text_input(key="tipo-0").set_value(" ")
    guardar(at)

    assert "tipo de sesión" in at.error[0].value
    assert casos.listar_sesiones(date.min, date.max) == []


def test_añadir_fila(abrir: Callable[[datetime], AppTest]) -> None:
    at = abrir(DE_DIA)

    at.button(key="añadir_fila").click().run()

    assert at.number_input(key="reps-0-4").value is None


def test_de_madrugada_pregunta_ayer_u_hoy(
    abrir: Callable[[datetime], AppTest], casos: CasosUsoTraining
) -> None:
    at = abrir(DE_MADRUGADA)
    assert at.radio[0].options == ["Ayer (13/11)", "Hoy (14/11)"] and not at.date_input

    at.radio[0].set_value(AYER)
    guardar(at)

    assert [s.logical_date for s in casos.listar_sesiones(date.min, date.max)] == [AYER]


def test_borrar_una_sesion(abrir: Callable[[datetime], AppTest], casos: CasosUsoTraining) -> None:
    casos.registrar_sesion(date(2026, 11, 10), "fuerza", [banca(8, 60)])
    at = abrir(DE_DIA)

    at.selectbox(key="sesion_a_borrar").select_index(0).run()
    at.button(key="borrar_sesion").click().run()

    assert not at.exception
    assert casos.listar_sesiones(date.min, date.max) == []
    assert "no hay sesiones" in at.info[-1].value


# --- Ayudas de presentación ----------------------------------------------------------------


def test_las_filas_se_agrupan_por_ejercicio_y_se_repiten_por_series() -> None:
    filas = [
        FilaEntreno("Press banca", 2, 8, 60.0, 7.5),
        FilaEntreno(None, 3, None, None),  # vacía: se ignora
        FilaEntreno("dominadas", 1, 10, None),  # sin peso: peso corporal
        FilaEntreno("press  BANCA", 1, 6, 65.0),  # mismo ejercicio escrito distinto
    ]

    ejercicios, errores = ejercicios_de_filas(filas)

    assert errores == []
    assert ejercicios == [
        {
            "nombre": "Press banca",
            "series": [
                {"reps": 8, "peso": 60.0, "rpe": 7.5},
                {"reps": 8, "peso": 60.0, "rpe": 7.5},
                {"reps": 6, "peso": 65.0, "rpe": None},
            ],
        },
        {"nombre": "dominadas", "series": [{"reps": 10, "peso": 0.0, "rpe": None}]},
    ]


def test_las_filas_a_medias_dan_error_con_su_numero() -> None:
    filas = [FilaEntreno("sentadilla", 3, None, 100.0), FilaEntreno("  ", 3, 5, 100.0)]

    ejercicios, errores = ejercicios_de_filas(filas)

    assert ejercicios == []
    assert errores == [
        "Fila 1: faltan las repeticiones de sentadilla.",
        "Fila 2: falta el ejercicio.",
    ]


def test_resumen_de_un_ejercicio_junta_las_series_iguales() -> None:
    (ejercicio,), _ = ejercicios_de_filas(
        [FilaEntreno("press banca", 3, 8, 60.0), FilaEntreno("press banca", 1, 6, 62.5)]
    )

    assert resumen_ejercicio(ejercicio) == "press banca 3x8x60, 1x6x62.5"


def test_graficas_de_entrenos() -> None:
    puntos = [(date(2026, 11, 10), 76.0), (date(2026, 11, 14), 81.7)]

    linea = grafica_progreso_1rm(puntos, "press banca")
    barras = grafica_volumen_semanal([(date(2026, 11, 9), 2310.0)])

    assert (linea.data[0].name, list(linea.data[0].y)) == ("1RM press banca", [76.0, 81.7])
    assert (barras.data[0].type, list(barras.data[0].y)) == ("bar", [2310.0])
