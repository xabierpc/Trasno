"""API del agente y prueba de extremo a extremo del hito 4 con un LLM falso y los módulos reales."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import agent
from agent.mensajes import ErrorLLM, Mensaje, RespuestaLLM
from core.bus import InMemoryEventBus
from core.config import Settings
from core.context import ContextoApp
from core.db import make_engine
from core.migraciones import migrar_todo
from interfaces.api.app import create_app
from tests.agente.conftest import LLMGuion, dice, llamada, pide

ICS = (
    "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:x\r\nBEGIN:VEVENT\r\nUID:calc\r\n"
    "SUMMARY:Clase de Cálculo\r\nDTSTART;TZID=Europe/Madrid:{dia}T090000\r\nDURATION:PT2H\r\n"
    "END:VEVENT\r\nEND:VCALENDAR\r\n"
)


class LLMRoto:
    def responder(
        self, mensajes: list[Mensaje], herramientas: list[dict[str, Any]]
    ) -> RespuestaLLM:
        raise ErrorLLM("No se puede contactar con el LLM")


@pytest.fixture
def llm() -> LLMGuion:
    return LLMGuion()


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, llm: LLMGuion) -> TestClient:
    """La API completa (todos los módulos y el agente) sobre un data/ temporal."""
    monkeypatch.setenv("TRASNO_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(agent, "crear_llm", lambda _settings: llm)
    migrar_todo()
    ctx = ContextoApp(
        bus=InMemoryEventBus(), engine_factory=make_engine, settings=Settings(_env_file=None)
    )
    return TestClient(create_app(ctx))


def chat(client: TestClient, *textos: str) -> dict[str, Any]:
    roles = ["user", "assistant"]
    mensajes = [{"rol": roles[n % 2], "contenido": t} for n, t in enumerate(textos)]
    respuesta = client.post("/agent/chat", json={"mensajes": mensajes})
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def test_herramientas_de_todos_los_modulos(client: TestClient) -> None:
    herramientas = {h["nombre"]: h for h in client.get("/agent/tools").json()}
    assert {"registrar_metrica", "agenda", "crear_tarea", "registrar_entreno"} <= set(herramientas)
    assert herramientas["crear_tarea"]["requiere_confirmacion"]
    assert not herramientas["registrar_metrica"]["requiere_confirmacion"]
    assert herramientas["registrar_metrica"]["sensible"]


def test_errores_de_la_api(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    solo_asistente = {"mensajes": [{"rol": "assistant", "contenido": "x"}]}
    assert client.post("/agent/chat", json=solo_asistente).status_code == 422
    assert client.post("/agent/chat", json={"mensajes": []}).status_code == 422
    assert client.post("/agent/confirm", json={"accion_id": 99}).status_code == 409


def test_llm_caido_es_502(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRASNO_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(agent, "crear_llm", lambda _settings: LLMRoto())
    migrar_todo()
    client = TestClient(create_app())

    respuesta = client.post("/agent/chat", json={"mensajes": [{"rol": "user", "contenido": "x"}]})
    assert respuesta.status_code == 502
    assert "No se puede contactar" in respuesta.json()["detail"]


def test_h4_de_extremo_a_extremo(client: TestClient, llm: LLMGuion) -> None:
    hoy = date.fromisoformat(client.get("/planning/agenda").json()["dia"])
    manana = hoy + timedelta(days=1)

    # 5. Importar un .ics añade las clases a la agenda
    importado = client.post(
        "/planning/import/ics",
        content=ICS.format(dia=f"{hoy:%Y%m%d}").encode(),
        headers={"Content-Type": "text/calendar"},
    ).json()
    assert importado["nuevos"] == 1

    # 1. «peso 74,3 y qué tengo hoy» registra el peso y devuelve la agenda
    llm._respuestas += [
        pide(
            llamada("registrar_metrica", nombre="peso", valor=74.3, fecha=hoy.isoformat()),
            llamada("agenda", id_llamada="c2", dia=hoy.isoformat()),
        ),
        dice("Apuntado. Hoy tienes Clase de Cálculo a las 9."),
    ]
    respuesta = chat(client, "peso 74,3 y qué tengo hoy")
    assert [a["herramienta"] for a in respuesta["ejecutadas"]] == ["registrar_metrica", "agenda"]
    assert all(a["estado"] == "ejecutada" for a in respuesta["ejecutadas"])
    assert "09:00-11:00 Clase de Cálculo" in respuesta["ejecutadas"][1]["resultado"]
    assert respuesta["propuestas"] == []

    # 2. «añade la tarea estudiar cálculo para mañana» pide confirmación…
    llm._respuestas += [
        pide(llamada("crear_tarea", titulo="estudiar cálculo", fecha=manana.isoformat())),
        dice("Voy a crear «estudiar cálculo» para mañana. ¿Lo confirmas?"),
    ]
    respuesta = chat(
        client,
        "peso 74,3 y qué tengo hoy",
        "Apuntado. Hoy tienes Clase de Cálculo a las 9.",
        "añade la tarea estudiar cálculo para mañana",
    )
    (propuesta,) = respuesta["propuestas"]
    assert propuesta["estado"] == "propuesta" and propuesta["descripcion"]
    agenda_manana = {"dia": manana.isoformat()}
    assert client.get("/planning/agenda", params=agenda_manana).json()["tareas"] == []
    # …y al confirmar aparece en la agenda de mañana (la de la página «Mañana»)
    confirmada = client.post("/agent/confirm", json={"accion_id": propuesta["id"]}).json()
    assert confirmada["estado"] == "ejecutada"
    tareas = client.get("/planning/agenda", params=agenda_manana).json()["tareas"]
    assert [t["titulo"] for t in tareas] == ["estudiar cálculo"]

    # 3. agent_log tiene las acciones
    log = [(a["herramienta"], a["estado"]) for a in client.get("/agent/actions").json()]
    assert ("registrar_metrica", "ejecutada") in log and ("crear_tarea", "ejecutada") in log

    # 4. El briefing incluye el peso nuevo
    seguimiento = {s["titulo"]: s["lineas"] for s in client.get("/briefing").json()["secciones"]}
    assert seguimiento["Seguimiento"][0] == "Peso: **74,3 kg** (hoy)"
