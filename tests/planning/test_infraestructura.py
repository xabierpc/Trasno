from __future__ import annotations

from datetime import date, time

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

from modules.planning.domain.eventos import BloqueRecurrente, Evento, OrigenEvento
from modules.planning.domain.tareas import Tarea
from modules.planning.infrastructure.modelos import Base
from modules.planning.infrastructure.repositorios import (
    RepositorioBloquesSQL,
    RepositorioEventosSQL,
    RepositorioTareasSQL,
)
from tests.planning.conftest import AHORA, LUNES, USER_ID, a_las

INSERT_TAREA = text(
    "INSERT INTO tarea (id, user_id, titulo, fecha, prioridad, estimacion_min, estado,"
    " creada_en, hecha_en) VALUES (:id, 1, 'x', NULL, :prioridad, :estimacion, :estado,"
    " '2026-11-14 09:30:00', :hecha_en)"
)
INSERT_EVENTO = text(
    "INSERT INTO evento (id, user_id, titulo, inicio, fin, lugar, origen, uid_externo)"
    " VALUES (:id, 1, 'x', :inicio, :fin, NULL, :origen, :uid)"
)
INSERT_BLOQUE = text(
    "INSERT INTO bloque (id, user_id, titulo, dia_semana, hora_inicio, hora_fin, desde, hasta,"
    " lugar) VALUES ('b', 1, 'x', :dia, :hora_inicio, :hora_fin, :desde, :hasta, NULL)"
)


def ejecutar(engine: Engine, sentencia: object, **parametros: object) -> None:
    with engine.begin() as conn:
        conn.execute(sentencia, parametros)  # type: ignore[arg-type]


def test_la_migracion_coincide_con_los_modelos(engine: Engine) -> None:
    with engine.connect() as conn:
        assert compare_metadata(MigrationContext.configure(conn), Base.metadata) == []


@pytest.mark.parametrize(
    "valores",
    [
        {"prioridad": "urgente"},
        {"estado": "a medias"},
        {"estimacion": 0},
        {"estado": "hecha"},  # hecha sin hecha_en
        {"hecha_en": "2026-11-14 10:00:00"},  # pendiente con hecha_en
    ],
)
def test_check_de_tarea(engine: Engine, valores: dict[str, object]) -> None:
    parametros = {
        "id": "t",
        "prioridad": "media",
        "estimacion": None,
        "estado": "pendiente",
        "hecha_en": None,
    }
    with pytest.raises(IntegrityError, match="CHECK"):
        ejecutar(engine, INSERT_TAREA, **{**parametros, **valores})


@pytest.mark.parametrize(
    "valores",
    [
        {"fin": "2026-11-16 08:00:00"},  # fin == inicio
        {"origen": "google"},
        {"origen": "ics", "uid": None},
    ],
)
def test_check_de_evento(engine: Engine, valores: dict[str, object]) -> None:
    parametros = {
        "id": "e",
        "inicio": "2026-11-16 08:00:00",
        "fin": "2026-11-16 09:00:00",
        "origen": "manual",
        "uid": None,
    }
    with pytest.raises(IntegrityError, match="CHECK"):
        ejecutar(engine, INSERT_EVENTO, **{**parametros, **valores})


def test_uid_de_ics_no_se_repite(engine: Engine) -> None:
    datos = {"inicio": "2026-11-16 08:00:00", "fin": "2026-11-16 09:00:00", "origen": "ics"}
    ejecutar(engine, INSERT_EVENTO, id="a", uid="clase-1", **datos)

    with pytest.raises(IntegrityError, match="UNIQUE"):
        ejecutar(engine, INSERT_EVENTO, id="b", uid="clase-1", **datos)


@pytest.mark.parametrize(
    "valores",
    [
        {"dia": 7},
        {"hora_fin": "09:00:00.000000"},  # igual que el inicio
        {"desde": "2026-12-01", "hasta": "2026-11-01"},
    ],
)
def test_check_de_bloque(engine: Engine, valores: dict[str, object]) -> None:
    parametros = {
        "dia": 0,
        "hora_inicio": "09:00:00.000000",
        "hora_fin": "11:00:00.000000",
        "desde": None,
        "hasta": None,
    }
    with pytest.raises(IntegrityError, match="CHECK"):
        ejecutar(engine, INSERT_BLOQUE, **{**parametros, **valores})


def test_guardar_dos_veces_actualiza_sin_duplicar(engine: Engine) -> None:
    repo = RepositorioTareasSQL(engine, USER_ID)
    tarea = Tarea(titulo="x", fecha=LUNES, creada_en=AHORA)
    repo.guardar(tarea)
    repo.guardar(tarea.completar(AHORA))

    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM tarea")).scalar_one() == 1
    assert repo.obtener(tarea.id) == tarea.completar(AHORA)


def test_los_datos_vuelven_iguales_de_la_bd(engine: Engine) -> None:
    """Fechas con zona, enums y horas sobreviven al viaje a SQLite."""
    eventos = RepositorioEventosSQL(engine, USER_ID)
    bloques = RepositorioBloquesSQL(engine, USER_ID)
    evento = Evento(
        titulo="Cálculo",
        inicio=a_las(9),
        fin=a_las(11),
        lugar="A1",
        origen=OrigenEvento.ICS,
        uid_externo="abc",
    )
    bloque = BloqueRecurrente(
        titulo="Física",
        dia_semana=2,
        hora_inicio=time(15, 30),
        hora_fin=time(17),
        desde=date(2026, 9, 1),
        hasta=date(2026, 12, 20),
    )
    eventos.guardar(evento)
    bloques.guardar(bloque)

    leido = eventos.por_uid("abc")
    assert leido == evento  # mismo instante aunque vuelva en UTC
    assert bloques.listar() == [bloque]


def test_cada_usuario_ve_solo_lo_suyo(engine: Engine) -> None:
    mia = RepositorioTareasSQL(engine, USER_ID)
    ajena = RepositorioTareasSQL(engine, 2)
    tarea = Tarea(titulo="x", fecha=LUNES, creada_en=AHORA)
    ajena.guardar(tarea)

    assert mia.del_dia(LUNES) == []
    assert mia.obtener(tarea.id) is None
    assert not mia.borrar(tarea.id)
    assert ajena.del_dia(LUNES) == [tarea]
