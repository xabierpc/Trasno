from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.bus import InMemoryEventBus
from core.config import Settings
from core.context import ContextoApp
from core.contracts import CadaDia, CadaIntervalo
from core.db import make_engine
from core.scheduler import Programador, Trabajo, TrabajoDuplicado, TrabajoNoEncontrado
from interfaces.api.app import create_app

ZONA = "Europe/Madrid"
MADRID = ZoneInfo(ZONA)
# Sábado 14/11/2026 a las 10:00 en Madrid
AHORA = datetime(2026, 11, 14, 10, 0, tzinfo=MADRID)


def nada() -> None:
    return None


def programador(*trabajos: Trabajo) -> Programador:
    return Programador(trabajos, ZONA)


# --- Disparadores ---------------------------------------------------------------------------


def test_cada_dia_a_una_hora_local():
    p = programador(Trabajo("briefing", nada, CadaDia(time(7, 30))))
    assert p.proximas(AHORA) == {"briefing": datetime(2026, 11, 15, 7, 30, tzinfo=MADRID)}

    temprano = AHORA.replace(hour=6)
    assert p.proximas(temprano)["briefing"] == datetime(2026, 11, 14, 7, 30, tzinfo=MADRID)


def test_cada_dia_solo_algunos_dias_de_la_semana():
    entre_semana = CadaDia(time(7, 30), dias=frozenset(range(5)))  # lunes a viernes
    p = programador(Trabajo("briefing", nada, entre_semana))
    # Es sábado: el siguiente es el lunes 16
    assert p.proximas(AHORA)["briefing"] == datetime(2026, 11, 16, 7, 30, tzinfo=MADRID)


def test_cada_dia_respeta_el_cambio_de_hora():
    p = programador(Trabajo("briefing", nada, CadaDia(time(7, 30))))
    antes_del_cambio = datetime(2026, 10, 24, 12, 0, tzinfo=MADRID)
    proxima = p.proximas(antes_del_cambio)["briefing"]
    assert proxima is not None
    assert proxima.astimezone(MADRID).hour == 7  # aunque el desfase con UTC haya cambiado


def test_cada_intervalo():
    p = programador(Trabajo("recordatorios", nada, CadaIntervalo(15)))
    proxima = p.proximas(AHORA)["recordatorios"]
    assert proxima is not None and proxima > AHORA


def test_intervalo_no_positivo_falla():
    with pytest.raises(ValueError, match="> 0"):
        programador(Trabajo("x", nada, CadaIntervalo(0)))


def test_nombres_duplicados_fallan_al_arrancar():
    with pytest.raises(TrabajoDuplicado):
        programador(Trabajo("x", nada, CadaIntervalo(5)), Trabajo("x", nada, CadaIntervalo(10)))


# --- Ejecución ------------------------------------------------------------------------------


def test_ejecutar_ahora():
    llamadas: list[str] = []
    p = programador(Trabajo("x", lambda: llamadas.append("x"), CadaIntervalo(60)))

    p.ejecutar_ahora("x")

    assert llamadas == ["x"]
    with pytest.raises(TrabajoNoEncontrado):
        p.ejecutar_ahora("no-existe")


def test_un_trabajo_que_falla_se_registra_y_no_se_propaga(caplog: pytest.LogCaptureFixture):
    def rompe() -> None:
        raise RuntimeError("boom")

    p = programador(Trabajo("roto", rompe, CadaIntervalo(60)))
    with caplog.at_level(logging.ERROR, logger="core.scheduler"):
        p.ejecutar_ahora("roto")

    assert "El trabajo roto ha fallado" in caplog.text


def test_arrancar_y_parar():
    p = programador(Trabajo("x", nada, CadaIntervalo(60)))
    p.arrancar()
    try:
        assert p.en_marcha
    finally:
        p.parar()
    assert not p.en_marcha


# --- Contexto y API -------------------------------------------------------------------------


def contexto(**ajustes: object) -> ContextoApp:
    return ContextoApp(
        bus=InMemoryEventBus(),
        engine_factory=make_engine,
        settings=Settings(_env_file=None, **ajustes),  # type: ignore[arg-type]
    )


def app_con_trabajo(ctx: ContextoApp, tarea: Callable[[], None] = nada) -> FastAPI:
    ctx.add_job("prueba.saludo", tarea, CadaDia(time(7, 30)))
    return create_app(ctx, paquete_modulos="modules", extras=())


def test_add_job_guarda_el_trabajo():
    ctx = contexto()
    ctx.add_job("a", nada, CadaIntervalo(5))
    assert [t.nombre for t in ctx.trabajos] == ["a"]


def test_la_api_lista_y_ejecuta_trabajos(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRASNO_DATA_DIR", str(tmp_path))
    llamadas: list[int] = []
    client = TestClient(app_con_trabajo(contexto(), lambda: llamadas.append(1)))

    trabajos = {t["nombre"]: t["proxima"] for t in client.get("/jobs").json()}
    assert trabajos["prueba.saludo"].endswith(("07:30:00+01:00", "07:30:00+02:00"))

    assert client.post("/jobs/prueba.saludo/run").status_code == 204
    assert llamadas == [1]
    assert client.post("/jobs/no-existe/run").status_code == 404


def test_el_programador_arranca_y_para_con_la_api(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TRASNO_DATA_DIR", str(tmp_path))
    app = app_con_trabajo(contexto())

    with TestClient(app):
        assert app.state.programador.en_marcha
    assert not app.state.programador.en_marcha


def test_con_el_scheduler_desactivado_no_arranca(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TRASNO_DATA_DIR", str(tmp_path))
    app = app_con_trabajo(contexto(scheduler_activo=False))

    with TestClient(app):
        assert not app.state.programador.en_marcha
