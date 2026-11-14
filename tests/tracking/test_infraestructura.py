from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import IntegrityError

import modules.tracking.infrastructure as infraestructura
from core.db import make_engine
from modules.tracking.domain.metricas import MetricDefinition, MetricEntry, TipoMetrica
from modules.tracking.infrastructure.modelos import Base
from modules.tracking.infrastructure.repositorios import (
    RepositorioEntradasSQL,
    RepositorioMetricasSQL,
)

HOY = date(2026, 11, 14)
MIGRACIONES = Path(infraestructura.__file__).parent / "migrations"
AHORA = datetime(2026, 11, 14, 9, 30, tzinfo=UTC)

INSERT_ENTRADA = text(
    "INSERT INTO metric_entry (id, user_id, metric_id, valor_num, valor_texto, timestamp,"
    " logical_date, slot) VALUES (:id, 1, :metric_id, :num, :texto, '2026-11-14 09:30:00',"
    " '2026-11-14', :slot)"
)


@pytest.fixture
def peso(engine: Engine) -> MetricDefinition:
    definicion = MetricDefinition(nombre="peso", unidad="kg", tipo=TipoMetrica.NUMERICA)
    RepositorioMetricasSQL(engine, 1).guardar(definicion)
    return definicion


def insertar(engine: Engine, **valores: object) -> None:
    parametros = {"id": "x", "num": 74.3, "texto": None, "slot": 0, **valores}
    with engine.begin() as conn:
        conn.execute(INSERT_ENTRADA, parametros)


def test_la_migracion_crea_el_mismo_esquema_que_los_modelos(engine: Engine) -> None:
    inspector = inspect(engine)

    for tabla in Base.metadata.sorted_tables:
        columnas = {c["name"] for c in inspector.get_columns(tabla.name)}
        assert columnas == {c.name for c in tabla.columns}


def test_duplicado_directo_hace_saltar_el_unique(engine: Engine, peso: MetricDefinition) -> None:
    insertar(engine, id="a", metric_id=peso.id)

    with pytest.raises(IntegrityError, match="UNIQUE"):
        insertar(engine, id="b", metric_id=peso.id)


def test_check_de_slot_y_de_un_solo_valor(engine: Engine, peso: MetricDefinition) -> None:
    with pytest.raises(IntegrityError, match="CHECK"):
        insertar(engine, metric_id=peso.id, slot=-1)
    with pytest.raises(IntegrityError, match="CHECK"):
        insertar(engine, metric_id=peso.id, num=None, texto=None)
    with pytest.raises(IntegrityError, match="CHECK"):
        insertar(engine, metric_id=peso.id, num=1.0, texto="a")


def test_check_de_tipo_en_la_definicion(engine: Engine) -> None:
    with pytest.raises(IntegrityError, match="CHECK"), engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO metric_definition (id, user_id, nombre, unidad, tipo, agregacion,"
                " on_duplicate, categorias) VALUES ('m', 1, 'x', '', 'raro', 'ultima',"
                " 'replace', '[]')"
            )
        )


def test_entrada_sin_metrica_viola_la_clave_foranea(engine: Engine) -> None:
    with pytest.raises(IntegrityError, match="FOREIGN KEY"):
        insertar(engine, metric_id="no-existe")


def test_borrar_la_metrica_borra_sus_entradas_en_cascada(
    engine: Engine, peso: MetricDefinition
) -> None:
    entradas = RepositorioEntradasSQL(engine, 1)
    entradas.guardar(peso.crear_entrada(74.3, timestamp=AHORA, logical_date=HOY))

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM metric_definition WHERE id = :id"), {"id": peso.id})

    with engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM metric_entry")) == 0


def test_cada_usuario_solo_ve_sus_datos(engine: Engine, peso: MetricDefinition) -> None:
    entrada: MetricEntry = RepositorioEntradasSQL(engine, 1).guardar(
        peso.crear_entrada(74.3, timestamp=AHORA, logical_date=HOY)
    )
    otro_metricas = RepositorioMetricasSQL(engine, 2)
    otro_entradas = RepositorioEntradasSQL(engine, 2)

    assert otro_metricas.listar() == []
    assert otro_entradas.listar(peso.id, HOY, HOY) == []
    assert otro_entradas.borrar(entrada.id) is False
    otro_metricas.guardar(MetricDefinition(nombre="peso", unidad="kg", tipo=TipoMetrica.NUMERICA))


def test_el_timestamp_vuelve_con_zona(engine: Engine, peso: MetricDefinition) -> None:
    entradas = RepositorioEntradasSQL(engine, 1)
    entradas.guardar(peso.crear_entrada(74.3, timestamp=AHORA, logical_date=HOY))

    assert entradas.listar(peso.id, HOY, HOY)[0].timestamp == AHORA


def test_la_migracion_0002_conserva_las_metricas_y_sus_entradas(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regresión: recrear metric_definition en modo batch borraba las entradas en cascada."""
    monkeypatch.setenv("TRASNO_DATA_DIR", str(tmp_path))
    config = Config()
    config.set_main_option("script_location", str(MIGRACIONES))
    engine = make_engine("tracking")
    try:
        with engine.begin() as conn:
            config.attributes["connection"] = conn
            command.upgrade(config, "0001")
            conn.execute(
                text(
                    "INSERT INTO metric_definition (id, user_id, nombre, unidad, tipo, agregacion,"
                    " on_duplicate, categorias) VALUES ('m', 1, 'peso', 'kg', 'numerica', 'media',"
                    " 'replace', '[]')"
                )
            )
            conn.execute(
                INSERT_ENTRADA, {"id": "e", "metric_id": "m", "num": 74.3, "texto": None, "slot": 0}
            )
        with engine.begin() as conn:
            config.attributes["connection"] = conn
            command.upgrade(config, "head")

        (peso,) = RepositorioMetricasSQL(engine, 1).listar()
        assert peso.activa is True
        entradas = RepositorioEntradasSQL(engine, 1).listar("m", date.min, date.max)
        assert [e.valor for e in entradas] == [74.3]
    finally:
        engine.dispose()
