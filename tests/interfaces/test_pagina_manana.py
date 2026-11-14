from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import streamlit as st
from fastapi import FastAPI
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from core.config import Settings
from interfaces.dashboard import cliente
from modules.planning.api import crear_router
from modules.planning.application.casos_uso import CasosUsoPlanning
from modules.planning.infrastructure.memoria import (
    RepositorioBloquesMemoria,
    RepositorioEventosMemoria,
    RepositorioTareasMemoria,
)

PAGINA = Path(__file__).resolve().parents[2] / "interfaces" / "dashboard" / "pages" / "4_Mañana.py"
ZONA = "Europe/Madrid"
# Sábado 14/11/2026: «mañana» es el domingo 15 y el lunes es el 16
AHORA = datetime(2026, 11, 14, 19, 0, tzinfo=ZoneInfo(ZONA))
HOY, MANANA, LUNES = date(2026, 11, 14), date(2026, 11, 15), date(2026, 11, 16)


@pytest.fixture(autouse=True)
def limpiar_cache() -> Iterator[None]:
    st.cache_resource.clear()
    yield
    st.cache_resource.clear()


@pytest.fixture
def casos() -> CasosUsoPlanning:
    return CasosUsoPlanning(
        RepositorioTareasMemoria(),
        RepositorioEventosMemoria(),
        RepositorioBloquesMemoria(),
        zona=ZONA,
        reloj=lambda: AHORA,
    )


@pytest.fixture
def abrir(casos: CasosUsoPlanning, monkeypatch: pytest.MonkeyPatch) -> Callable[[], AppTest]:
    """Abre la página contra una API de planning en memoria."""

    def _abrir() -> AppTest:
        api = FastAPI()
        api.include_router(crear_router(casos, Settings(_env_file=None), reloj=lambda: AHORA))
        monkeypatch.setattr(cliente, "_crear_cliente", lambda: TestClient(api))
        return AppTest.from_file(str(PAGINA)).run()

    return _abrir


def textos(at: AppTest) -> str:
    return "\n".join(m.value for m in at.markdown)


def test_por_defecto_enseña_mañana(abrir: Callable[[], AppTest], casos: CasosUsoPlanning):
    casos.crear_tarea("estudiar cálculo", fecha=MANANA)
    casos.crear_tarea("de hoy", fecha=HOY)
    at = abrir()

    assert not at.exception
    assert at.subheader[0].value == "Domingo 15/11/2026"
    assert [c.label for c in at.checkbox] == ["🟡 estudiar cálculo"]


def test_añadir_tarea_al_dia_elegido(abrir: Callable[[], AppTest], casos: CasosUsoPlanning):
    at = abrir()

    at.text_input(key="tarea_titulo").set_value("repasar física")
    at.selectbox(key="tarea_prioridad").set_value("alta")
    at.button(key="crear_tarea").click().run()

    assert not at.exception and not at.error
    (tarea,) = casos.agenda(MANANA).tareas
    assert (tarea.titulo, tarea.prioridad.value) == ("repasar física", "alta")
    assert "Tarea añadida al 15/11" in at.success[0].value
    assert [c.label for c in at.checkbox] == ["🔴 repasar física"]


def test_marcar_y_desmarcar_una_tarea(abrir: Callable[[], AppTest], casos: CasosUsoPlanning):
    tarea = casos.crear_tarea("x", fecha=MANANA)
    at = abrir()

    at.checkbox(key=f"tarea-{tarea.id}").check().run()
    assert casos.agenda(MANANA).tareas[0].hecha

    at.checkbox(key=f"tarea-{tarea.id}").uncheck().run()
    assert not casos.agenda(MANANA).tareas[0].hecha


def test_pasar_una_atrasada_al_dia(abrir: Callable[[], AppTest], casos: CasosUsoPlanning):
    vieja = casos.crear_tarea("vieja", fecha=date(2026, 11, 10))
    at = abrir()

    at.button(key=f"mover-{vieja.id}").click().run()

    assert [t.id for t in casos.agenda(MANANA).tareas] == [vieja.id]


def test_horario_con_clase_y_evento_y_aviso_de_solape(
    abrir: Callable[[], AppTest], casos: CasosUsoPlanning
):
    casos.crear_bloque("Cálculo", dia_semana=0, hora_inicio=time(9), hora_fin=time(11))
    at = abrir()
    at.radio(key="dia").set_value("Otro").run()
    at.date_input(key="otro_dia").set_value(LUNES).run()

    at.text_input(key="evento_titulo").set_value("Médico")
    at.time_input(key="evento_inicio").set_value(time(10))
    at.time_input(key="evento_fin").set_value(time(12))
    at.button(key="crear_evento").click().run()

    assert not at.exception and not at.error
    assert "Se pisa con «Cálculo»" in at.warning[0].value
    assert "**09:00-11:00** Cálculo _(clase)_" in textos(at)
    assert "**10:00-12:00** Médico" in textos(at)


def test_error_de_la_api_se_muestra(abrir: Callable[[], AppTest], casos: CasosUsoPlanning):
    at = abrir()

    at.button(key="crear_tarea").click().run()  # título vacío

    assert "vacío" in at.error[0].value
    assert casos.agenda(MANANA).tareas == []


def test_añadir_y_borrar_un_bloque(abrir: Callable[[], AppTest], casos: CasosUsoPlanning):
    at = abrir()

    at.text_input(key="bloque_titulo").set_value("Física")
    at.selectbox(key="bloque_dia").set_value(2)
    at.button(key="crear_bloque").click().run()

    (bloque,) = casos.listar_bloques()
    assert (bloque.titulo, bloque.dia_semana) == ("Física", 2)

    at.button(key=f"borrar-{bloque.id}").click().run()
    assert casos.listar_bloques() == []
