from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine

import modules.training as training
from core.bus import InMemoryEventBus
from core.config import Settings
from core.context import ContextoApp
from modules.training.domain.eventos import SesionBorrada, SesionRegistrada

BANCA = {
    "nombre": "Press banca",
    "series": [{"reps": 8, "peso": 60, "rpe": 7.5}, {"reps": 6, "peso": 65}],
}
SESION = {
    "logical_date": "2026-11-14",
    "tipo": "fuerza",
    "duracion_min": 55,
    "energia_previa": 7,
    "ejercicios": [BANCA],
}


@pytest.fixture
def ctx(engine: Engine) -> ContextoApp:
    ctx = ContextoApp(
        bus=InMemoryEventBus(),
        engine_factory=lambda _nombre: engine,
        settings=Settings(_env_file=None),
    )
    training.register(ctx)
    return ctx


@pytest.fixture
def client(ctx: ContextoApp) -> TestClient:
    """API con solo el router de training, sobre un training.sqlite temporal."""
    app = FastAPI()
    for router in ctx.routers:
        app.include_router(router)
    return TestClient(app)


def registrar(client: TestClient, **cambios: object) -> dict:
    respuesta = client.post("/training/sessions", json={**SESION, **cambios})
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def test_registrar_devuelve_la_sesion_con_su_volumen(client: TestClient) -> None:
    sesion = registrar(client)

    assert sesion["volumen"] == 870
    assert sesion["records"] == []
    assert sesion["ejercicios"][0]["nombre"] == "press banca"
    assert sesion["ejercicios"][0]["series"][0] == {"reps": 8, "peso": 60.0, "rpe": 7.5}
    assert client.get("/training/sessions").json() == [
        {k: v for k, v in sesion.items() if k != "records"}
    ]


def test_registrar_devuelve_los_records_batidos(client: TestClient) -> None:
    registrar(client, logical_date="2026-11-10")

    mejor = {"nombre": "press banca", "series": [{"reps": 3, "peso": 75}]}
    sesion = registrar(client, ejercicios=[mejor])

    assert [(r["tipo"], r["valor"], r["anterior"]) for r in sesion["records"]] == [
        ("peso", 75.0, 65.0),
        ("1rm", 82.5, 78.0),
    ]


def test_sesion_minima_sin_ejercicios(client: TestClient) -> None:
    sesion = registrar(client, tipo="cardio", duracion_min=None, energia_previa=None, ejercicios=[])

    assert (sesion["volumen"], sesion["duracion_min"], sesion["ejercicios"]) == (0, None, [])


@pytest.mark.parametrize(
    "cambios",
    [
        {"tipo": " "},
        {"energia_previa": 11},
        {"duracion_min": 0},
        {"ejercicios": [{"nombre": "press banca", "series": []}]},
        {"ejercicios": [{"nombre": "press banca", "series": [{"reps": 0, "peso": 60}]}]},
        {"ejercicios": [{"nombre": "press banca", "series": [{"reps": 8.5, "peso": 60}]}]},
        {"logical_date": None},
    ],
)
def test_sesion_invalida_devuelve_422_y_no_guarda(client: TestClient, cambios: dict) -> None:
    respuesta = client.post("/training/sessions", json={**SESION, **cambios})

    assert respuesta.status_code == 422
    assert client.get("/training/sessions").json() == []


def test_listar_filtra_por_fechas(client: TestClient) -> None:
    for dia in ("2026-11-10", "2026-11-12", "2026-11-14"):
        registrar(client, logical_date=dia)

    sesiones = client.get(
        "/training/sessions", params={"desde": "2026-11-11", "hasta": "2026-11-12"}
    ).json()

    assert [s["logical_date"] for s in sesiones] == ["2026-11-12"]


def test_borrar_sesion(client: TestClient) -> None:
    sesion = registrar(client)

    assert client.delete(f"/training/sessions/{sesion['id']}").status_code == 204
    assert client.get("/training/sessions").json() == []
    assert client.delete(f"/training/sessions/{sesion['id']}").status_code == 404


def test_ejercicios_progreso_records_y_volumen_semanal(client: TestClient) -> None:
    registrar(client, logical_date="2026-11-10")
    registrar(client, ejercicios=[{"nombre": "press banca", "series": [{"reps": 3, "peso": 75}]}])

    assert client.get("/training/exercises").json() == ["press banca"]
    progreso = client.get("/training/exercises/Press Banca/progress").json()
    assert [(p["logical_date"], p["un_rm"], p["peso_maximo"], p["volumen"]) for p in progreso] == [
        ("2026-11-10", 78.0, 65.0, 870.0),
        ("2026-11-14", 82.5, 75.0, 225.0),
    ]
    assert client.get("/training/exercises/peso muerto/progress").status_code == 404
    (records,) = client.get("/training/records").json()
    assert records["un_rm"] == {"valor": 82.5, "logical_date": "2026-11-14"}
    assert records["volumen"] == {"valor": 870.0, "logical_date": "2026-11-10"}
    assert client.get("/training/weekly-volume").json() == [
        {"semana": "2026-11-09", "volumen": 1095.0}
    ]


def test_publica_sesion_registrada_y_sesion_borrada(ctx: ContextoApp, client: TestClient) -> None:
    registradas: list[SesionRegistrada] = []
    borradas: list[SesionBorrada] = []
    ctx.bus.subscribe(SesionRegistrada, registradas.append)
    ctx.bus.subscribe(SesionBorrada, borradas.append)

    sesion = registrar(client)
    client.post("/training/sessions", json={**SESION, "tipo": ""})
    client.delete(f"/training/sessions/{sesion['id']}")

    assert [(e.sesion_id, e.tipo, e.volumen) for e in registradas] == [
        (sesion["id"], "fuerza", 870)
    ]
    assert str(registradas[0].logical_date) == "2026-11-14"
    assert [e.sesion_id for e in borradas] == [sesion["id"]]


def test_register_añade_el_proveedor_de_series(ctx: ContextoApp, client: TestClient) -> None:
    registrar(client)

    (proveedor,) = ctx.series_providers()

    assert [s.nombre for s in proveedor.list_series()] == ["volumen_semanal", "1rm press banca"]
