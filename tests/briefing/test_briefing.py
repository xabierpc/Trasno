from __future__ import annotations

import logging
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from modules.briefing.api import crear_router
from modules.briefing.application.casos_uso import CasosUsoBriefing
from modules.briefing.domain.briefing import Briefing, Seccion
from modules.briefing.infrastructure import notificador as modulo_notificador
from modules.briefing.infrastructure.notificador import NotificadorEscritorio

ZONA = "Europe/Madrid"
MADRID = ZoneInfo(ZONA)
# Lunes 16/11/2026 a las 7:30
AHORA = datetime(2026, 11, 16, 7, 30, tzinfo=MADRID)
LUNES = date(2026, 11, 16)


class SeccionFalsa:
    def __init__(self, titulo: str, orden: int, lineas: list[str] | Exception) -> None:
        self.titulo, self.orden, self._lineas = titulo, orden, lineas
        self.dias: list[date] = []

    def lineas(self, dia: date) -> list[str]:
        self.dias.append(dia)
        if isinstance(self._lineas, Exception):
            raise self._lineas
        return self._lineas


class NotificadorFalso:
    def __init__(self) -> None:
        self.avisos: list[tuple[str, str]] = []

    def notificar(self, titulo: str, texto: str) -> None:
        self.avisos.append((titulo, texto))


def casos(
    *secciones: SeccionFalsa, notificador: NotificadorFalso | None = None
) -> CasosUsoBriefing:
    return CasosUsoBriefing(
        lambda: list(secciones),
        zona=ZONA,
        notificador=notificador or NotificadorFalso(),
        reloj=lambda: AHORA,
    )


# --- Dominio --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("hora", "saludo"), [(7, "Buenos días"), (16, "Buenas tardes"), (23, "Buenas noches")]
)
def test_saludo_segun_la_hora(hora: int, saludo: str):
    briefing = Briefing(dia=LUNES, generado_en=AHORA.replace(hour=hora), secciones=[])
    assert briefing.saludo == f"{saludo}. Hoy es lunes 16/11."


def test_markdown():
    briefing = Briefing(
        dia=LUNES, generado_en=AHORA, secciones=[Seccion("Hoy", ["**09:00** Cálculo", "x"])]
    )
    assert briefing.markdown() == (
        "Buenos días. Hoy es lunes 16/11.\n\n**Hoy**\n- **09:00** Cálculo\n- x"
    )
    vacio = Briefing(dia=LUNES, generado_en=AHORA, secciones=[])
    assert vacio.markdown().endswith("Nada que contar por ahora.")


# --- Casos de uso ---------------------------------------------------------------------------


def test_ordena_las_secciones_y_omite_las_vacias():
    entreno = SeccionFalsa("Entreno", 30, ["e"])
    hoy = SeccionFalsa("Hoy", 10, ["h"])
    vacia = SeccionFalsa("Vacía", 20, [])

    briefing = casos(entreno, vacia, hoy).briefing()

    assert briefing.dia == LUNES
    assert [s.titulo for s in briefing.secciones] == ["Hoy", "Entreno"]
    assert hoy.dias == [LUNES]


def test_una_seccion_que_falla_no_rompe_el_briefing(caplog: pytest.LogCaptureFixture):
    rota = SeccionFalsa("Rota", 10, RuntimeError("boom"))
    buena = SeccionFalsa("Buena", 20, ["ok"])

    with caplog.at_level(logging.ERROR):
        briefing = casos(rota, buena).briefing()

    assert [(s.titulo, s.lineas) for s in briefing.secciones] == [
        ("Rota", ["_(no se ha podido generar)_"]),
        ("Buena", ["ok"]),
    ]
    assert "La sección 'Rota' del briefing ha fallado" in caplog.text


def test_briefing_de_otro_dia():
    seccion = SeccionFalsa("Hoy", 10, ["x"])
    assert casos(seccion).briefing(date(2026, 11, 20)).dia == date(2026, 11, 20)
    assert seccion.dias == [date(2026, 11, 20)]


def test_enviar_notifica_en_texto_plano():
    notificador = NotificadorFalso()
    casos(
        SeccionFalsa("Hoy", 10, ["**09:00** _Cálculo_"]), notificador=notificador
    ).enviar_briefing()

    ((titulo, texto),) = notificador.avisos
    assert titulo == "Trasno · briefing"
    assert texto == "Buenos días. Hoy es lunes 16/11.\nHoy:\n  • 09:00 Cálculo"


# --- Notificador de escritorio --------------------------------------------------------------


def test_notificador_sin_notify_send_solo_registra(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
):
    monkeypatch.setattr(modulo_notificador.shutil, "which", lambda _p: None)
    llamadas: list[object] = []
    monkeypatch.setattr(modulo_notificador.subprocess, "run", lambda *a, **k: llamadas.append(a))

    with caplog.at_level(logging.INFO):
        NotificadorEscritorio().notificar("Título", "Texto")

    assert llamadas == [] and "Título" in caplog.text


def test_notificador_con_notify_send(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(modulo_notificador.shutil, "which", lambda _p: "/usr/bin/notify-send")
    llamadas: list[list[str]] = []
    monkeypatch.setattr(
        modulo_notificador.subprocess, "run", lambda args, **_k: llamadas.append(args)
    )

    NotificadorEscritorio().notificar("Título", "Texto")

    assert llamadas == [
        ["/usr/bin/notify-send", "--app-name=Trasno", "--expire-time=60000", "Título", "Texto"]
    ]


def test_notificador_que_falla_no_rompe(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(modulo_notificador.shutil, "which", lambda _p: "/usr/bin/notify-send")

    def falla(*_a: object, **_k: object) -> None:
        raise OSError("sin pantalla")

    monkeypatch.setattr(modulo_notificador.subprocess, "run", falla)
    NotificadorEscritorio().notificar("Título", "Texto")  # no lanza


# --- API ------------------------------------------------------------------------------------


def test_api_devuelve_el_briefing():
    app = FastAPI()
    app.include_router(crear_router(casos(SeccionFalsa("Hoy", 10, ["x"]))))
    client = TestClient(app)

    respuesta = client.get("/briefing").json()
    assert respuesta["dia"] == "2026-11-16"
    assert respuesta["secciones"] == [{"titulo": "Hoy", "lineas": ["x"]}]
    assert respuesta["markdown"].startswith("Buenos días")
    assert client.get("/briefing", params={"dia": "2026-11-20"}).json()["dia"] == "2026-11-20"
