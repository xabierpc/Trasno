from __future__ import annotations

import pytest
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import IntegrityError

from modules.training.application.casos_uso import CasosUsoTraining
from modules.training.infrastructure.modelos import Base
from modules.training.infrastructure.repositorios import RepositorioSesionesSQL
from tests.training.conftest import AHORA, D14, ejercicio

INSERT_SESION = text(
    "INSERT INTO sesion (id, user_id, logical_date, tipo, duracion_min, energia_previa, timestamp)"
    " VALUES (:id, 1, '2026-11-14', 'fuerza', :duracion, :energia, '2026-11-14 19:00:00')"
)
INSERT_EJERCICIO = text(
    "INSERT INTO ejercicio (id, user_id, sesion_id, orden, nombre)"
    " VALUES (:id, 1, :sesion_id, :orden, 'press banca')"
)
INSERT_SERIE = text(
    "INSERT INTO serie (id, user_id, ejercicio_id, orden, reps, peso, rpe)"
    " VALUES (:id, 1, :ejercicio_id, :orden, :reps, :peso, :rpe)"
)


def contar(engine: Engine, tabla: str) -> int:
    with engine.connect() as conn:
        return conn.execute(text(f"SELECT COUNT(*) FROM {tabla}")).scalar_one()


@pytest.fixture
def con_ejercicio(engine: Engine) -> Engine:
    """Una sesión «s» con un ejercicio «e», insertados sin pasar por el caso de uso."""
    with engine.begin() as conn:
        conn.execute(INSERT_SESION, {"id": "s", "duracion": 60, "energia": 7})
        conn.execute(INSERT_EJERCICIO, {"id": "e", "sesion_id": "s", "orden": 0})
    return engine


def serie(engine: Engine, **valores: object) -> None:
    parametros = {"id": "x", "ejercicio_id": "e", "orden": 0, "reps": 8, "peso": 60, "rpe": None}
    with engine.begin() as conn:
        conn.execute(INSERT_SERIE, {**parametros, **valores})


def test_la_migracion_crea_el_mismo_esquema_que_los_modelos(engine: Engine) -> None:
    inspector = inspect(engine)

    assert set(Base.metadata.tables) <= set(inspector.get_table_names())
    for tabla in Base.metadata.sorted_tables:
        columnas = {c["name"] for c in inspector.get_columns(tabla.name)}
        assert columnas == {c.name for c in tabla.columns}
        indices = {i["name"] for i in inspector.get_indexes(tabla.name)}
        assert indices == {i.name for i in tabla.indexes}


@pytest.mark.parametrize("valores", [{"reps": 0}, {"peso": -1}, {"rpe": 11}, {"rpe": 0}])
def test_check_de_las_series(con_ejercicio: Engine, valores: dict[str, object]) -> None:
    with pytest.raises(IntegrityError, match="CHECK"):
        serie(con_ejercicio, **valores)


@pytest.mark.parametrize("valores", [{"duracion": 0}, {"energia": 0}, {"energia": 11}])
def test_check_de_la_sesion(engine: Engine, valores: dict[str, object]) -> None:
    parametros = {"id": "s", "duracion": None, "energia": None, **valores}

    with pytest.raises(IntegrityError, match="CHECK"), engine.begin() as conn:
        conn.execute(INSERT_SESION, parametros)


def test_orden_repetido_hace_saltar_el_unique(con_ejercicio: Engine) -> None:
    serie(con_ejercicio, id="a")

    with pytest.raises(IntegrityError, match="UNIQUE"):
        serie(con_ejercicio, id="b")
    with pytest.raises(IntegrityError, match="UNIQUE"), con_ejercicio.begin() as conn:
        conn.execute(INSERT_EJERCICIO, {"id": "e2", "sesion_id": "s", "orden": 0})


def test_serie_sin_ejercicio_viola_la_clave_foranea(engine: Engine) -> None:
    with pytest.raises(IntegrityError, match="FOREIGN KEY"):
        serie(engine, ejercicio_id="no-existe")


def test_borrar_la_sesion_borra_ejercicios_y_series_en_cascada(engine: Engine) -> None:
    casos = CasosUsoTraining(RepositorioSesionesSQL(engine, 1), reloj=lambda: AHORA)
    guardada = casos.registrar_sesion(
        D14, "fuerza", [ejercicio("press banca", (8, 60), (8, 60)), ejercicio("remo", (10, 40))]
    )
    assert (contar(engine, "ejercicio"), contar(engine, "serie")) == (2, 3)

    casos.borrar_sesion(guardada.sesion.id)

    assert [contar(engine, t) for t in ("sesion", "ejercicio", "serie")] == [0, 0, 0]


def test_cada_usuario_solo_ve_sus_sesiones(engine: Engine) -> None:
    mio, ajeno = RepositorioSesionesSQL(engine, 1), RepositorioSesionesSQL(engine, 2)
    guardada = CasosUsoTraining(mio, reloj=lambda: AHORA).registrar_sesion(D14, "cardio")

    assert ajeno.listar(D14, D14) == []
    assert ajeno.borrar(guardada.sesion.id) is False
    assert len(mio.listar(D14, D14)) == 1
