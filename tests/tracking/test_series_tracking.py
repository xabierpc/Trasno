from __future__ import annotations

from datetime import date

import pytest

from core.contracts import SeriesProvider
from modules.tracking.application.casos_uso import CasosUsoTracking
from modules.tracking.application.ports import RepositorioEntradas, RepositorioMetricas
from modules.tracking.application.series import ProveedorSeriesTracking
from modules.tracking.domain.errores import MetricaNoEncontrada
from modules.tracking.domain.metricas import Agregacion, PoliticaDuplicado, TipoMetrica

D12, D13, D14 = date(2026, 11, 12), date(2026, 11, 13), date(2026, 11, 14)


@pytest.fixture
def proveedor(
    repos: tuple[RepositorioMetricas, RepositorioEntradas],
) -> ProveedorSeriesTracking:
    return ProveedorSeriesTracking(*repos)


def crear(casos: CasosUsoTracking, nombre: str, agregacion: Agregacion) -> None:
    casos.crear_metrica(
        nombre,
        "u",
        TipoMetrica.NUMERICA,
        agregacion=agregacion,
        on_duplicate=PoliticaDuplicado.KEEP_ALL,
    )
    for dia, valor in [(D14, 3.0), (D12, 1.0), (D12, 2.0), (D12, 6.0)]:
        casos.registrar_metrica(nombre, valor, dia)


def test_cumple_el_contrato_series_provider(proveedor: ProveedorSeriesTracking) -> None:
    assert isinstance(proveedor, SeriesProvider)


def test_lista_las_metricas_menos_las_categoricas(
    casos: CasosUsoTracking, proveedor: ProveedorSeriesTracking
) -> None:
    casos.crear_metrica("peso", "kg", TipoMetrica.NUMERICA)
    casos.crear_metrica("leer", "", TipoMetrica.BOOLEANA)
    casos.crear_metrica("ocio", "", TipoMetrica.CATEGORICA, categorias=("leer", "jugar"))

    series = proveedor.list_series()

    assert [(s.nombre, s.unidad) for s in series] == [("leer", ""), ("peso", "kg")]


@pytest.mark.parametrize(
    ("agregacion", "valor_d12"),
    [(Agregacion.SUMA, 9.0), (Agregacion.MEDIA, 3.0), (Agregacion.ULTIMA, 6.0)],
)
def test_un_valor_por_dia_segun_la_agregacion(
    casos: CasosUsoTracking,
    proveedor: ProveedorSeriesTracking,
    agregacion: Agregacion,
    valor_d12: float,
) -> None:
    crear(casos, "m", agregacion)

    assert proveedor.get_series("m", D12, D14) == [(D12, valor_d12), (D14, 3.0)]
    assert proveedor.get_series("m", D13, D13) == []


def test_las_booleanas_salen_como_cero_y_uno(
    casos: CasosUsoTracking, proveedor: ProveedorSeriesTracking
) -> None:
    casos.crear_metrica("leer", "", TipoMetrica.BOOLEANA)
    casos.registrar_metrica("leer", True, D12)
    casos.registrar_metrica("leer", False, D13)

    assert proveedor.get_series("leer", D12, D14) == [(D12, 1.0), (D13, 0.0)]


def test_serie_inexistente_o_categorica_falla(
    casos: CasosUsoTracking, proveedor: ProveedorSeriesTracking
) -> None:
    casos.crear_metrica("ocio", "", TipoMetrica.CATEGORICA, categorias=("leer",))

    with pytest.raises(MetricaNoEncontrada):
        proveedor.get_series("nada", D12, D14)
    with pytest.raises(MetricaNoEncontrada):
        proveedor.get_series("ocio", D12, D14)
