from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import date
from pathlib import Path
from typing import Any

import pytest
import streamlit as st
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from agent.api import crear_router
from agent.mensajes import ErrorLLM, Mensaje, RespuestaLLM
from core.acciones import RegistroAccionesSQL
from core.contracts import Tool
from core.db import make_engine
from interfaces.dashboard import cliente
from tests.agente.conftest import ALEMBIC_INI, Agenda, LLMGuion, crear_agente, dice, llamada, pide

# La página pide más tiempo de espera al LLM; el TestClient de Starlette avisa de que lo ignora.
pytestmark = pytest.mark.filterwarnings("ignore:You should not use the 'timeout' argument")

PAGINA = Path(__file__).resolve().parents[2] / "interfaces" / "dashboard" / "pages" / "6_Trasno.py"


class LLMRoto:
    def responder(
        self, mensajes: list[Mensaje], herramientas: list[dict[str, Any]]
    ) -> RespuestaLLM:
        raise ErrorLLM("No se puede contactar con el LLM")


@pytest.fixture(autouse=True)
def limpiar_cache() -> Iterator[None]:
    st.cache_resource.clear()
    yield
    st.cache_resource.clear()


@pytest.fixture
def acciones(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[RegistroAccionesSQL]:
    monkeypatch.setenv("TRASNO_DATA_DIR", str(tmp_path))
    command.upgrade(Config(str(ALEMBIC_INI)), "head")
    engine = make_engine("core")
    yield RegistroAccionesSQL(engine, 1)
    engine.dispose()


@pytest.fixture
def agenda() -> Agenda:
    return Agenda()


@pytest.fixture
def abrir(
    acciones: RegistroAccionesSQL, agenda: Agenda, monkeypatch: pytest.MonkeyPatch
) -> Callable[[Any], AppTest]:
    """Abre la página contra la API real del agente, con un LLM falso y herramientas falsas."""

    def _abrir(llm: Any) -> AppTest:
        herramientas = [
            Tool(nombre="crear_tarea", funcion=agenda.crear_tarea, requiere_confirmacion=True),
            Tool(nombre="registrar_peso", funcion=agenda.registrar_peso),
        ]
        agente = crear_agente(llm, herramientas, acciones)
        api = FastAPI()
        api.include_router(crear_router(agente, lambda: herramientas, lambda: acciones))
        monkeypatch.setattr(cliente, "_crear_cliente", lambda: TestClient(api))
        return AppTest.from_file(str(PAGINA)).run()

    return _abrir


def boton(at: AppTest, prefijo: str) -> Any:
    return next(b for b in at.button if b.key.startswith(prefijo))


def escribir(at: AppTest, texto: str) -> AppTest:
    return at.chat_input(key="trasno_entrada").set_value(texto).run()


def test_conversacion_con_herramienta_ejecutada(abrir: Callable[[Any], AppTest]):
    llm = LLMGuion(
        pide(llamada("registrar_peso", kg=74.3, fecha="2026-11-16")),
        dice("Apuntado, **74,3 kg**."),
        dice("De nada."),
    )
    at = abrir(llm)
    assert "Pídeme cosas" in at.caption[0].value

    escribir(at, "peso 74,3")

    assert not at.exception and not at.error
    usuario, asistente = at.chat_message
    assert usuario.markdown[0].value == "peso 74,3"
    assert asistente.markdown[0].value == "Apuntado, **74,3 kg**."
    assert at.expander[0].label == "Qué he hecho (1)"
    assert "✓ `registrar_peso` · Peso 74.3 el 2026-11-16" in at.expander[0].markdown[0].value

    escribir(at, "gracias")
    # El historial completo viaja en cada mensaje: usuario, asistente, usuario
    assert [m.contenido for m in llm.recibidos[-1][1:]] == [
        "peso 74,3",
        "Apuntado, **74,3 kg**.",
        "gracias",
    ]


def test_confirmar_una_propuesta(abrir: Callable[[Any], AppTest], agenda: Agenda):
    llm = LLMGuion(
        pide(llamada("crear_tarea", titulo="estudiar cálculo", fecha="2026-11-17")),
        dice("¿Creo la tarea?"),
    )
    at = escribir(abrir(llm), "añade estudiar cálculo para mañana")

    assert "titulo: estudiar cálculo · fecha: 2026-11-17" in at.caption[-1].value
    assert agenda.tareas == []
    boton(at, "confirmar-").click().run()

    assert agenda.tareas == [("estudiar cálculo", date(2026, 11, 17))]
    assert "✅ Hecho: Tarea creada: estudiar cálculo" in "\n".join(m.value for m in at.markdown)
    assert not [b for b in at.button if b.key.startswith("confirmar-")]


def test_cancelar_una_propuesta(abrir: Callable[[Any], AppTest], agenda: Agenda):
    llm = LLMGuion(pide(llamada("crear_tarea", titulo="x")), dice("¿Seguro?"))
    at = escribir(abrir(llm), "añade x")

    boton(at, "cancelar-").click().run()

    assert agenda.tareas == []
    assert "✖️ Cancelado" in "\n".join(m.value for m in at.markdown)


def test_si_el_llm_falla_se_avisa_y_se_puede_repetir(abrir: Callable[[Any], AppTest]):
    at = escribir(abrir(LLMRoto()), "hola")

    assert "No se puede contactar con el LLM" in at.error[0].value
    assert at.session_state["trasno_mensajes"] == []  # se puede volver a mandar
    at.run()
    assert len(at.chat_message) == 0


def test_nueva_conversacion(abrir: Callable[[Any], AppTest]):
    at = escribir(abrir(LLMGuion(dice("Hola."))), "hola")
    assert len(at.chat_message) == 2

    at.button(key="nueva_conversacion").click().run()

    assert len(at.chat_message) == 0
