"""Briefing con los módulos reales: lo que registra cada uno aparece en el resumen."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from core.bus import InMemoryEventBus
from core.config import Settings
from core.context import ContextoApp
from core.db import make_engine
from core.migraciones import migrar_todo
from interfaces.api.app import create_app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("TRASNO_DATA_DIR", str(tmp_path))
    migrar_todo()
    ctx = ContextoApp(
        bus=InMemoryEventBus(), engine_factory=make_engine, settings=Settings(_env_file=None)
    )
    return TestClient(create_app(ctx, extras=()))


def test_el_briefing_junta_agenda_peso_y_entreno(client: TestClient) -> None:
    hoy = client.get("/planning/agenda").json()["dia"]
    peso = {"metric": "peso", "valor": 74.3, "logical_date": hoy}
    assert client.post("/tracking/entries", json=peso).status_code == 201
    client.post("/planning/tasks", json={"titulo": "estudiar cálculo", "fecha": hoy})
    client.post(
        "/planning/events",
        json={"titulo": "Cálculo", "inicio": f"{hoy}T09:00", "fin": f"{hoy}T11:00"},
    )
    client.post("/training/sessions", json={"logical_date": hoy, "tipo": "fuerza"})

    briefing = client.get("/briefing").json()

    secciones = {s["titulo"]: s["lineas"] for s in briefing["secciones"]}
    assert list(secciones) == ["Hoy", "Seguimiento", "Entreno"]
    assert secciones["Hoy"] == ["**09:00-11:00** Cálculo", "Tarea: estudiar cálculo"]
    assert secciones["Seguimiento"] == ["Peso: **74,3 kg** (hoy)"]
    assert secciones["Entreno"][0] == "Último entreno: fuerza, hoy"


def test_el_briefing_esta_programado_a_su_hora(client: TestClient) -> None:
    trabajos = {t["nombre"]: t["proxima"] for t in client.get("/jobs").json()}
    proxima = datetime.fromisoformat(trabajos["briefing.diario"])
    assert (proxima.hour, proxima.minute) == (7, 30)
