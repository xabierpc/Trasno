from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine

import modules.tracking as tracking
from core.bus import InMemoryEventBus
from core.config import Settings
from core.context import ContextoApp
from modules.tracking.api import crear_router
from modules.tracking.application.casos_uso import CasosUsoTracking
from modules.tracking.domain.eventos import MetricaRegistrada
from modules.tracking.domain.metricas import TipoMetrica
from modules.tracking.infrastructure.memoria import (
    RepositorioEntradasMemoria,
    RepositorioMetricasMemoria,
)

PESO = {"nombre": "peso", "unidad": "kg", "tipo": "numerica", "agregacion": "media"}
MADRID = ZoneInfo("Europe/Madrid")


@pytest.fixture
def ctx(engine: Engine) -> ContextoApp:
    ctx = ContextoApp(
        bus=InMemoryEventBus(),
        engine_factory=lambda _nombre: engine,
        settings=Settings(_env_file=None),
    )
    tracking.register(ctx)
    return ctx


@pytest.fixture
def client(ctx: ContextoApp) -> TestClient:
    """API con solo el router de tracking, sobre un tracking.sqlite temporal."""
    app = FastAPI()
    for router in ctx.routers:
        app.include_router(router)
    return TestClient(app)


def registrar(client: TestClient, valor: object, dia: str = "2026-11-14") -> dict:
    respuesta = client.post(
        "/tracking/entries", json={"metric": "peso", "valor": valor, "logical_date": dia}
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def test_crear_y_listar_metricas(client: TestClient) -> None:
    creada = client.post("/tracking/metrics", json=PESO)

    assert creada.status_code == 201
    assert creada.json()["on_duplicate"] == "replace"
    assert [m["nombre"] for m in client.get("/tracking/metrics").json()] == ["peso"]


def test_metrica_repetida_devuelve_409_e_invalida_422(client: TestClient) -> None:
    client.post("/tracking/metrics", json=PESO)

    assert client.post("/tracking/metrics", json=PESO).status_code == 409
    escala_sin_maximo = {"nombre": "animo", "tipo": "escala"}
    respuesta = client.post("/tracking/metrics", json=escala_sin_maximo)
    assert respuesta.status_code == 422
    assert "escala_max" in respuesta.json()["detail"]


def test_registrar_dos_veces_el_mismo_dia_deja_una_entrada(client: TestClient) -> None:
    client.post("/tracking/metrics", json=PESO)
    primera = registrar(client, 74.3)
    segunda = registrar(client, 74)

    entradas = client.get("/tracking/entries", params={"metric": "peso"}).json()

    assert [(e["valor"], e["slot"]) for e in entradas] == [(74.0, 0)]
    assert primera["id"] == segunda["id"] == entradas[0]["id"]
    assert datetime.fromisoformat(entradas[0]["timestamp"]).tzinfo is not None


def test_listar_filtra_por_fechas(client: TestClient) -> None:
    client.post("/tracking/metrics", json=PESO)
    for dia in ("2026-11-10", "2026-11-12", "2026-11-14"):
        registrar(client, 75.0, dia)

    entradas = client.get(
        "/tracking/entries", params={"metric": "peso", "desde": "2026-11-11", "hasta": "2026-11-12"}
    ).json()

    assert [e["logical_date"] for e in entradas] == ["2026-11-12"]


def test_errores_de_registro(client: TestClient) -> None:
    client.post("/tracking/metrics", json=PESO)
    cuerpo = {"metric": "peso", "valor": 74.3, "logical_date": "2026-11-14"}

    assert client.post("/tracking/entries", json={**cuerpo, "metric": "altura"}).status_code == 404
    assert client.post("/tracking/entries", json={**cuerpo, "valor": "mucho"}).status_code == 422
    sin_fecha = {"metric": "peso", "valor": 74.3}
    assert client.post("/tracking/entries", json=sin_fecha).status_code == 422
    assert client.get("/tracking/entries", params={"metric": "altura"}).status_code == 404


def test_valores_booleanos_y_categoricos_viajan_con_su_tipo(client: TestClient) -> None:
    client.post("/tracking/metrics", json={"nombre": "leer", "tipo": "booleana"})
    client.post(
        "/tracking/metrics",
        json={"nombre": "ocio", "tipo": "categorica", "categorias": ["leer", "jugar"]},
    )
    for metrica, valor in [("leer", True), ("ocio", "jugar")]:
        cuerpo = {"metric": metrica, "valor": valor, "logical_date": "2026-11-14"}
        assert client.post("/tracking/entries", json=cuerpo).status_code == 201

    assert client.get("/tracking/entries", params={"metric": "leer"}).json()[0]["valor"] is True
    assert client.get("/tracking/entries", params={"metric": "ocio"}).json()[0]["valor"] == "jugar"
    un_uno = {"metric": "leer", "valor": 1, "logical_date": "2026-11-14"}
    assert client.post("/tracking/entries", json=un_uno).status_code == 422


def test_borrar_entrada(client: TestClient) -> None:
    client.post("/tracking/metrics", json=PESO)
    entrada = registrar(client, 74.3)

    assert client.delete(f"/tracking/entries/{entrada['id']}").status_code == 204
    assert client.get("/tracking/entries", params={"metric": "peso"}).json() == []
    assert client.delete(f"/tracking/entries/{entrada['id']}").status_code == 404


def test_registrar_publica_metrica_registrada(ctx: ContextoApp, client: TestClient) -> None:
    eventos: list[MetricaRegistrada] = []
    ctx.bus.subscribe(MetricaRegistrada, eventos.append)
    client.post("/tracking/metrics", json=PESO)

    entrada = registrar(client, 74.3)
    rechazada = {"metric": "peso", "valor": "mucho", "logical_date": "2026-11-14"}
    client.post("/tracking/entries", json=rechazada)

    assert [(e.metrica, e.entrada_id, e.valor) for e in eventos] == [("peso", entrada["id"], 74.3)]
    assert str(eventos[0].logical_date) == "2026-11-14"


def test_register_añade_el_proveedor_de_series(ctx: ContextoApp, client: TestClient) -> None:
    client.post("/tracking/metrics", json=PESO)

    (proveedor,) = ctx.series_providers()

    assert [s.nombre for s in proveedor.list_series()] == ["peso"]


@pytest.mark.parametrize(
    ("ahora", "madrugada", "ayer", "hoy"),
    [
        (datetime(2026, 11, 14, 1, 30, tzinfo=MADRID), True, "2026-11-13", "2026-11-14"),
        (datetime(2026, 11, 14, 9, 0, tzinfo=MADRID), False, "2026-11-13", "2026-11-14"),
        # 23:30 UTC ya es el día siguiente (00:30) en Madrid
        (datetime(2026, 11, 14, 23, 30, tzinfo=UTC), True, "2026-11-14", "2026-11-15"),
    ],
)
def test_fecha_logica_avisa_de_la_madrugada(
    ahora: datetime, madrugada: bool, ayer: str, hoy: str
) -> None:
    casos = CasosUsoTracking(RepositorioMetricasMemoria(), RepositorioEntradasMemoria())
    app = FastAPI()
    app.include_router(crear_router(casos, Settings(_env_file=None), reloj=lambda: ahora))

    respuesta = TestClient(app).get("/tracking/fecha-logica")

    assert respuesta.json() == {"es_madrugada": madrugada, "ayer": ayer, "hoy": hoy}


def test_racha_por_api_con_hoy_explicito(client: TestClient) -> None:
    client.post("/tracking/metrics", json={"nombre": "leer", "tipo": "booleana"})
    for dia, hecho in [("2026-11-11", True), ("2026-11-12", False), ("2026-11-13", True)]:
        cuerpo = {"metric": "leer", "valor": hecho, "logical_date": dia}
        assert client.post("/tracking/entries", json=cuerpo).status_code == 201

    racha = client.get("/tracking/metrics/leer/racha", params={"hoy": "2026-11-14"})

    assert racha.status_code == 200
    assert racha.json() == {
        "metric": "leer",
        "actual": 1,
        "maxima": 1,
        "semanal": {"cumplidos": 2, "dias": 7, "porcentaje": 28.6},
        "mensual": {"cumplidos": 2, "dias": 30, "porcentaje": 6.7},
    }
    assert client.get("/tracking/metrics/nada/racha").status_code == 404


def test_racha_sin_hoy_usa_la_fecha_local_del_reloj() -> None:
    casos = CasosUsoTracking(RepositorioMetricasMemoria(), RepositorioEntradasMemoria())
    casos.crear_metrica("leer", "", TipoMetrica.BOOLEANA)
    casos.registrar_metrica("leer", True, date(2026, 11, 15))
    app = FastAPI()
    # 23:30 UTC del día 14 ya es el día 15 en Madrid
    ahora = datetime(2026, 11, 14, 23, 30, tzinfo=UTC)
    app.include_router(crear_router(casos, Settings(_env_file=None), reloj=lambda: ahora))

    assert TestClient(app).get("/tracking/metrics/leer/racha").json()["actual"] == 1


def test_desactivar_y_filtrar_metricas_activas(client: TestClient) -> None:
    client.post("/tracking/metrics", json=PESO)
    client.post("/tracking/metrics", json={"nombre": "leer", "tipo": "booleana"})

    cambiada = client.patch("/tracking/metrics/leer", json={"activa": False})

    assert cambiada.status_code == 200 and cambiada.json()["activa"] is False
    activas = client.get("/tracking/metrics", params={"activas": True}).json()
    assert [m["nombre"] for m in activas] == ["peso"]
    assert [m["activa"] for m in client.get("/tracking/metrics").json()] == [False, True]
    assert client.patch("/tracking/metrics/nada", json={"activa": False}).status_code == 404
