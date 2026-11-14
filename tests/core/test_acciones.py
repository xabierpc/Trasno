from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, text

import core
from core.acciones import AccionNoEncontrada, RegistroAccionesSQL
from core.bus import InMemoryEventBus
from core.config import Settings
from core.context import ContextoApp
from core.contracts import Accion, EstadoAccion
from core.db import make_engine

ALEMBIC_INI = Path(core.__file__).parent / "migrations" / "alembic.ini"
AHORA = datetime(2026, 11, 14, 10, 0, tzinfo=UTC)


@pytest.fixture
def engine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    monkeypatch.setenv("TRASNO_DATA_DIR", str(tmp_path))
    command.upgrade(Config(str(ALEMBIC_INI)), "head")
    engine = make_engine("core")
    yield engine
    engine.dispose()


def accion(herramienta: str = "crear_tarea", minutos: int = 0, **cambios: object) -> Accion:
    datos = {
        "herramienta": herramienta,
        "argumentos": {"titulo": "estudiar cálculo", "fecha": "2026-11-15"},
        "estado": EstadoAccion.PROPUESTA,
        "timestamp": AHORA + timedelta(minutes=minutos),
    }
    return Accion(**{**datos, **cambios})  # type: ignore[arg-type]


def test_guardar_obtener_y_confirmar(engine: Engine):
    registro = RegistroAccionesSQL(engine, 1)

    guardada = registro.guardar(accion())
    assert guardada.id is not None
    assert registro.obtener(guardada.id) == guardada

    ejecutada = registro.cambiar_estado(guardada.id, EstadoAccion.EJECUTADA, "Tarea creada")
    assert (ejecutada.estado, ejecutada.resultado) == (EstadoAccion.EJECUTADA, "Tarea creada")
    assert registro.obtener(guardada.id) == ejecutada
    assert ejecutada.timestamp == AHORA


def test_recientes_de_la_mas_nueva_a_la_mas_antigua(engine: Engine):
    registro = RegistroAccionesSQL(engine, 1)
    for minutos, nombre in enumerate(["a", "b", "c"]):
        registro.guardar(accion(nombre, minutos))

    assert [a.herramienta for a in registro.recientes()] == ["c", "b", "a"]
    assert [a.herramienta for a in registro.recientes(limite=2)] == ["c", "b"]


def test_cada_usuario_ve_solo_lo_suyo(engine: Engine):
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO user (id, nombre) VALUES (2, 'otro')"))
    mio, ajeno = RegistroAccionesSQL(engine, 1), RegistroAccionesSQL(engine, 2)
    suya = ajeno.guardar(accion())
    assert suya.id is not None

    assert mio.obtener(suya.id) is None
    assert mio.recientes() == []
    with pytest.raises(AccionNoEncontrada):
        mio.cambiar_estado(suya.id, EstadoAccion.CANCELADA)


def test_la_migracion_0002_marca_las_acciones_viejas_como_ejecutadas(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("TRASNO_DATA_DIR", str(tmp_path))
    config = Config(str(ALEMBIC_INI))
    command.upgrade(config, "0001")
    engine = make_engine("core")
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO agent_log (user_id, herramienta, argumentos, resultado, timestamp)"
                    " VALUES (1, 'registrar_metrica', '{}', 'ok', '2026-11-14 09:00:00')"
                )
            )
        command.upgrade(config, "head")

        (vieja,) = RegistroAccionesSQL(engine, 1).recientes()
        assert vieja.estado is EstadoAccion.EJECUTADA
    finally:
        engine.dispose()


def test_el_contexto_abre_el_registro_del_core_al_usarlo(engine: Engine):
    pedidos: list[str] = []

    def fabrica(nombre: str) -> Engine:
        pedidos.append(nombre)
        return engine

    ctx = ContextoApp(
        bus=InMemoryEventBus(), engine_factory=fabrica, settings=Settings(_env_file=None)
    )
    assert pedidos == []  # no se abre nada hasta que alguien lo usa
    ctx.acciones.guardar(accion())
    assert pedidos == ["core"]
    assert len(ctx.acciones.recientes()) == 1
