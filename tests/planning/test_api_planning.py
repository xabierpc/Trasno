from __future__ import annotations

from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine

import modules.planning as planning
from core.bus import InMemoryEventBus
from core.config import Settings
from core.context import ContextoApp
from modules.planning.api import crear_router
from modules.planning.application.casos_uso import CasosUsoPlanning
from tests.planning.conftest import MADRID, ZONA, Repos

# Sábado 14/11/2026 a las 10:00 en Madrid
AHORA = datetime(2026, 11, 14, 10, 0, tzinfo=MADRID)


@pytest.fixture
def client(repos: Repos) -> TestClient:
    """API con solo el router de planning; corre contra memoria y contra SQL."""
    casos = CasosUsoPlanning(*repos, zona=ZONA, reloj=lambda: AHORA)
    app = FastAPI()
    app.include_router(crear_router(casos, Settings(_env_file=None), reloj=lambda: AHORA))
    return TestClient(app)


def crear_tarea(client: TestClient, **datos: object) -> dict:
    respuesta = client.post("/planning/tasks", json={"titulo": "estudiar cálculo", **datos})
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def test_register_monta_el_router(engine: Engine) -> None:
    ctx = ContextoApp(
        bus=InMemoryEventBus(), engine_factory=lambda _n: engine, settings=Settings(_env_file=None)
    )
    planning.register(ctx)
    app = FastAPI()
    for router in ctx.routers:
        app.include_router(router)

    assert TestClient(app).get("/planning/agenda").status_code == 200


def test_agenda_por_defecto_es_la_de_hoy(client: TestClient) -> None:
    crear_tarea(client, fecha="2026-11-14")
    agenda = client.get("/planning/agenda").json()

    assert agenda["dia"] == "2026-11-14"
    assert [t["titulo"] for t in agenda["tareas"]] == ["estudiar cálculo"]


def test_crear_completar_reabrir_mover_y_borrar_tarea(client: TestClient) -> None:
    tarea = crear_tarea(client, fecha="2026-11-15", prioridad="alta", estimacion_min=60)
    assert (tarea["estado"], tarea["prioridad"]) == ("pendiente", "alta")

    ruta = f"/planning/tasks/{tarea['id']}"
    assert client.post(f"{ruta}/complete").json()["estado"] == "hecha"
    assert client.post(f"{ruta}/reopen").json()["estado"] == "pendiente"
    assert client.post(f"{ruta}/move", json={"fecha": None}).json()["fecha"] is None
    assert [t["id"] for t in client.get("/planning/tasks/inbox").json()] == [tarea["id"]]

    assert client.delete(ruta).status_code == 204
    assert client.delete(ruta).status_code == 404


def test_errores_de_dominio_son_422(client: TestClient) -> None:
    respuesta = client.post("/planning/tasks", json={"titulo": "   "})
    assert respuesta.status_code == 422
    assert "vacío" in respuesta.json()["detail"]


def test_tarea_inexistente_es_404(client: TestClient) -> None:
    assert client.post("/planning/tasks/no-existe/complete").status_code == 404


def test_evento_con_hora_local_sin_zona_y_aviso_de_solape(client: TestClient) -> None:
    clase = {"titulo": "Cálculo", "dia_semana": 0, "hora_inicio": "09:00", "hora_fin": "11:00"}
    assert client.post("/planning/blocks", json=clase).status_code == 201

    respuesta = client.post(
        "/planning/events",
        json={"titulo": "Médico", "inicio": "2026-11-16T10:00", "fin": "2026-11-16T12:00"},
    )

    assert respuesta.status_code == 201
    guardado = respuesta.json()
    assert guardado["evento"]["inicio"] == "2026-11-16T10:00:00+01:00"
    assert [a["titulo"] for a in guardado["avisos"]] == ["Cálculo"]

    citas = client.get("/planning/agenda", params={"dia": "2026-11-16"}).json()["citas"]
    assert [(c["titulo"], c["tipo"]) for c in citas] == [
        ("Cálculo", "bloque"),
        ("Médico", "evento"),
    ]


def test_mover_y_borrar_evento(client: TestClient) -> None:
    evento = client.post(
        "/planning/events",
        json={"titulo": "x", "inicio": "2026-11-16T10:00", "fin": "2026-11-16T11:00"},
    ).json()["evento"]
    ruta = f"/planning/events/{evento['id']}"

    movido = client.post(
        f"{ruta}/move", json={"inicio": "2026-11-16T12:00", "fin": "2026-11-16T13:00"}
    )
    assert movido.json()["evento"]["inicio"] == "2026-11-16T12:00:00+01:00"
    assert client.delete(ruta).status_code == 204
    assert client.delete(ruta).status_code == 404


def test_evento_que_termina_antes_de_empezar_es_422(client: TestClient) -> None:
    respuesta = client.post(
        "/planning/events",
        json={"titulo": "x", "inicio": "2026-11-16T12:00", "fin": "2026-11-16T11:00"},
    )
    assert respuesta.status_code == 422


def test_bloques_listar_avisar_y_borrar(client: TestClient) -> None:
    base = {"dia_semana": 0, "hora_inicio": "09:00", "hora_fin": "11:00"}
    calculo = client.post("/planning/blocks", json={"titulo": "Cálculo", **base}).json()
    fisica = client.post("/planning/blocks", json={"titulo": "Física", **base}).json()

    assert [b["titulo"] for b in fisica["avisos"]] == ["Cálculo"]
    assert len(client.get("/planning/blocks").json()) == 2
    assert client.delete(f"/planning/blocks/{calculo['bloque']['id']}").status_code == 204
    assert (
        client.post("/planning/blocks", json={"titulo": "x", **base, "dia_semana": 7}).status_code
        == 422
    )
