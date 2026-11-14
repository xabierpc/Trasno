from __future__ import annotations

from sqlalchemy import Engine, text

from core.migraciones import migrar_todo
from modules.tracking.domain.metricas import Agregacion, PoliticaDuplicado, TipoMetrica
from modules.tracking.infrastructure.repositorios import RepositorioMetricasSQL


def test_migrate_crea_la_metrica_peso(engine_migrado: Engine) -> None:
    (peso,) = RepositorioMetricasSQL(engine_migrado, 1).listar()

    assert (peso.nombre, peso.unidad, peso.tipo) == ("peso", "kg", TipoMetrica.NUMERICA)
    assert peso.agregacion is Agregacion.MEDIA
    assert peso.on_duplicate is PoliticaDuplicado.REPLACE


def test_migrar_dos_veces_no_duplica_ni_pisa_cambios(engine_migrado: Engine) -> None:
    with engine_migrado.begin() as conn:
        conn.execute(text("UPDATE metric_definition SET objetivo = 72 WHERE nombre = 'peso'"))

    migrar_todo()

    (peso,) = RepositorioMetricasSQL(engine_migrado, 1).listar()
    assert peso.objetivo == 72
