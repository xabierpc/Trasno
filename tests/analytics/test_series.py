from __future__ import annotations

import ast
import math
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

import modules.analytics
from core.bus import InMemoryEventBus
from core.config import Settings
from core.context import ContextoApp
from core.contracts import SeriesInfo
from core.db import make_engine
from modules.analytics.application.series import (
    CatalogoSeries,
    correlacion,
    medias_moviles,
    unir_series,
)
from modules.analytics.domain.errores import SerieDuplicada, SerieNoEncontrada


def d(dia: int) -> date:
    return date(2026, 11, dia)


@dataclass
class ProveedorFalso:
    """SeriesProvider en memoria: {nombre: (unidad, puntos)}."""

    series: dict[str, tuple[str, list[tuple[date, float]]]] = field(default_factory=dict)

    def list_series(self) -> list[SeriesInfo]:
        return [SeriesInfo(nombre=n, unidad=u) for n, (u, _) in self.series.items()]

    def get_series(self, nombre: str, desde: date, hasta: date) -> list[tuple[date, float]]:
        return [(f, v) for f, v in self.series[nombre][1] if desde <= f <= hasta]


# Fechas desalineadas: el peso se mide los días 1, 2 y 4; los pasos, del 2 al 5.
PESO = ProveedorFalso({"peso": ("kg", [(d(1), 70.0), (d(2), 71.0), (d(4), 73.0)])})
PASOS = ProveedorFalso(
    {"pasos": ("pasos", [(d(2), 1000.0), (d(3), 2000.0), (d(4), 3000.0), (d(5), 4000.0)])}
)


@pytest.fixture
def ctx() -> ContextoApp:
    return ContextoApp(
        bus=InMemoryEventBus(), engine_factory=make_engine, settings=Settings(_env_file=None)
    )


@pytest.fixture
def catalogo(ctx: ContextoApp) -> CatalogoSeries:
    catalogo = CatalogoSeries(ctx.series_providers)
    # Se registran después de crear el catálogo: el orden de carga de módulos no importa.
    ctx.add_series_provider(PESO)
    ctx.add_series_provider(PASOS)
    return catalogo


def test_catalogo_lista_las_series_de_todos_los_proveedores(catalogo: CatalogoSeries) -> None:
    assert [s.nombre for s in catalogo.listar()] == ["peso", "pasos"]


def test_catalogo_pide_cada_serie_a_su_proveedor(catalogo: CatalogoSeries) -> None:
    assert catalogo.obtener("pasos", d(3), d(4)) == [(d(3), 2000.0), (d(4), 3000.0)]


def test_serie_desconocida_lanza_error_de_dominio(catalogo: CatalogoSeries) -> None:
    with pytest.raises(SerieNoEncontrada):
        catalogo.obtener("sueño", d(1), d(5))


def test_serie_ofrecida_por_dos_proveedores_es_un_error(
    ctx: ContextoApp, catalogo: CatalogoSeries
) -> None:
    ctx.add_series_provider(ProveedorFalso({"peso": ("lb", [])}))

    with pytest.raises(SerieDuplicada):
        catalogo.obtener("peso", d(1), d(5))


def test_unir_series_hace_outer_join_con_huecos_nan(catalogo: CatalogoSeries) -> None:
    tabla = catalogo.tabla(["peso", "pasos"], d(1), d(5))

    assert list(tabla.columns) == ["peso", "pasos"]
    assert list(tabla.index.date) == [d(1), d(2), d(3), d(4), d(5)]
    assert tabla.loc["2026-11-01", "peso"] == 70.0
    assert math.isnan(tabla.loc["2026-11-01", "pasos"])
    assert math.isnan(tabla.loc["2026-11-03", "peso"])
    assert math.isnan(tabla.loc["2026-11-05", "peso"])


def test_unir_series_vacias_da_tabla_vacia() -> None:
    tabla = unir_series({"peso": [], "pasos": []})

    assert tabla.empty
    assert list(tabla.columns) == ["peso", "pasos"]


def test_media_movil_usa_dias_de_calendario_e_ignora_huecos(catalogo: CatalogoSeries) -> None:
    medias = medias_moviles(catalogo.tabla(["peso"], d(1), d(5)), dias=2)

    # Ventana de 2 días: día 2 → media(70, 71); día 4 → solo 73 (el día 3 no hay dato).
    assert medias["peso"].tolist() == [70.0, 70.5, 73.0]


def test_correlacion_usa_solo_las_fechas_comunes() -> None:
    tabla = unir_series(
        {
            "a": [(d(1), 1.0), (d(2), 2.0), (d(3), 3.0), (d(4), 4.0)],
            "b": [(d(2), 10.0), (d(3), 20.0), (d(4), 30.0), (d(5), 0.0)],
        }
    )

    matriz = correlacion(tabla)

    assert matriz.loc["a", "b"] == pytest.approx(1.0)
    assert isinstance(matriz, pd.DataFrame)


def test_analytics_no_importa_ningun_otro_modulo() -> None:
    raiz = Path(modules.analytics.__file__).parent
    importados = set()
    for fichero in raiz.rglob("*.py"):
        for nodo in ast.walk(ast.parse(fichero.read_text(encoding="utf-8"))):
            if isinstance(nodo, ast.ImportFrom) and nodo.module:
                importados.add(nodo.module)
            elif isinstance(nodo, ast.Import):
                importados.update(alias.name for alias in nodo.names)

    ajenos = {
        m for m in importados if m.startswith("modules.") and not m.startswith("modules.analytics")
    }
    assert ajenos == set()
