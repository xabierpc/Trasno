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

from interfaces.dashboard import cliente
from modules.briefing.api import crear_router
from modules.briefing.application.casos_uso import CasosUsoBriefing

PAGINA = (
    Path(__file__).resolve().parents[2] / "interfaces" / "dashboard" / "pages" / "5_Briefing.py"
)
MADRID = ZoneInfo("Europe/Madrid")
AHORA = datetime(2026, 11, 16, 7, 30, tzinfo=MADRID)


class SeccionHoy:
    titulo, orden = "Hoy", 10

    def lineas(self, dia: date) -> list[str]:
        return [f"**09:00-11:00** Cálculo ({dia:%d/%m})"]


class NotificadorFalso:
    def __init__(self, enviados: list[int]) -> None:
        self._enviados = enviados

    def notificar(self, titulo: str, texto: str) -> None:
        self._enviados.append(1)


@pytest.fixture(autouse=True)
def limpiar_cache() -> Iterator[None]:
    st.cache_resource.clear()
    yield
    st.cache_resource.clear()


@pytest.fixture
def enviados() -> list[int]:
    return []


@pytest.fixture
def abrir(enviados: list[int], monkeypatch: pytest.MonkeyPatch) -> Callable[[], AppTest]:
    def _abrir() -> AppTest:
        casos = CasosUsoBriefing(
            lambda: [SeccionHoy()],
            zona="Europe/Madrid",
            notificador=NotificadorFalso(enviados),
            reloj=lambda: AHORA,
        )
        api = FastAPI()
        api.include_router(crear_router(casos))

        @api.get("/jobs")
        def jobs() -> list[dict[str, str]]:
            return [{"nombre": "briefing.diario", "proxima": "2026-11-17T07:30:00+01:00"}]

        @api.post("/jobs/{nombre}/run", status_code=204)
        def run(nombre: str) -> None:
            casos.enviar_briefing()

        monkeypatch.setattr(cliente, "_crear_cliente", lambda: TestClient(api))
        return AppTest.from_file(str(PAGINA)).run()

    return _abrir


def test_enseña_el_briefing_de_hoy(abrir: Callable[[], AppTest]) -> None:
    at = abrir()

    assert not at.exception
    texto = "\n".join(m.value for m in at.markdown)
    assert "Buenos días. Hoy es lunes 16/11." in texto
    assert "**09:00-11:00** Cálculo (16/11)" in texto
    assert "2026-11-17 a las 07:30" in at.caption[0].value


def test_otro_dia(abrir: Callable[[], AppTest]) -> None:
    at = abrir()
    at.date_input(key="dia_briefing").set_value(date(2026, 11, 18)).run()

    assert "Cálculo (18/11)" in "\n".join(m.value for m in at.markdown)


def test_enviar_ahora(abrir: Callable[[], AppTest], enviados: list[int]) -> None:
    at = abrir()
    at.button(key="enviar_briefing").click().run()

    assert enviados == [1]
    assert at.success[0].value == "Briefing enviado."
