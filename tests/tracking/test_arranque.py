from __future__ import annotations

from sqlalchemy import Engine, text

from core.migraciones import migrar_todo
from modules.tracking.domain.metricas import (
    Agregacion,
    MetricDefinition,
    PoliticaDuplicado,
    TipoMetrica,
)
from modules.tracking.infrastructure.arranque import HABITOS
from modules.tracking.infrastructure.repositorios import RepositorioMetricasSQL


def metricas(engine: Engine) -> dict[str, MetricDefinition]:
    return {m.nombre: m for m in RepositorioMetricasSQL(engine, 1).listar()}


def test_migrate_crea_la_metrica_peso(engine_migrado: Engine) -> None:
    peso = metricas(engine_migrado)["peso"]

    assert (peso.nombre, peso.unidad, peso.tipo) == ("peso", "kg", TipoMetrica.NUMERICA)
    assert peso.agregacion is Agregacion.MEDIA
    assert peso.on_duplicate is PoliticaDuplicado.REPLACE


def test_migrate_crea_pasos_sueño_animo_energia_y_habitos(engine_migrado: Engine) -> None:
    creadas = metricas(engine_migrado)

    assert set(creadas) == {"peso", "pasos", "sueño", "ánimo", "energía", *HABITOS}
    pasos, sueño = creadas["pasos"], creadas["sueño"]
    assert (pasos.tipo, pasos.agregacion, pasos.objetivo) == (
        TipoMetrica.CONTEO,
        Agregacion.SUMA,
        8000,
    )
    assert (sueño.tipo, sueño.unidad, sueño.objetivo) == (TipoMetrica.DURACION, "min", 420)
    for nombre in ("ánimo", "energía"):
        assert (creadas[nombre].tipo, creadas[nombre].escala_max) == (TipoMetrica.ESCALA, 10)
    assert all(creadas[h].tipo is TipoMetrica.BOOLEANA for h in HABITOS)
    assert all(m.activa for m in creadas.values())


def test_migrar_dos_veces_no_duplica_ni_pisa_cambios(engine_migrado: Engine) -> None:
    antes = len(metricas(engine_migrado))
    with engine_migrado.begin() as conn:
        conn.execute(text("UPDATE metric_definition SET objetivo = 72 WHERE nombre = 'peso'"))
        conn.execute(text("UPDATE metric_definition SET activa = 0 WHERE nombre = 'meditar'"))

    migrar_todo()

    despues = metricas(engine_migrado)
    assert len(despues) == antes
    assert despues["peso"].objetivo == 72
    assert despues["meditar"].activa is False
