from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from modules.tracking.application.casos_uso import CasosUsoTracking
from modules.tracking.domain.errores import MetricaNoEncontrada
from modules.tracking.domain.metricas import (
    Agregacion,
    MetricDefinition,
    MetricEntry,
    PoliticaDuplicado,
    TipoMetrica,
)
from modules.tracking.domain.rachas import (
    Cumplimiento,
    Racha,
    calcular_racha,
    cumplimiento,
    dias_cumplidos,
)

HOY = date(2026, 11, 14)
AHORA = datetime(2026, 11, 14, 9, 30, tzinfo=UTC)


def hace(dias: int) -> date:
    return HOY - timedelta(days=dias)


def entradas(definicion: MetricDefinition, valores: dict[date, object]) -> list[MetricEntry]:
    return [
        definicion.crear_entrada(valor, timestamp=AHORA, logical_date=dia)
        for dia, valor in valores.items()
    ]


# --- Racha ---------------------------------------------------------------------------------


def test_sin_dias_cumplidos_no_hay_racha() -> None:
    assert calcular_racha(set(), HOY) == Racha(actual=0, maxima=0)


def test_dias_seguidos_hasta_hoy() -> None:
    assert calcular_racha({hace(2), hace(1), HOY}, HOY) == Racha(actual=3, maxima=3)


def test_hoy_sin_registrar_no_rompe_la_racha() -> None:
    assert calcular_racha({hace(3), hace(2), hace(1)}, HOY) == Racha(actual=3, maxima=3)


def test_ayer_y_hoy_sin_registrar_rompen_la_racha() -> None:
    assert calcular_racha({hace(4), hace(3), hace(2)}, HOY) == Racha(actual=0, maxima=3)


def test_un_dia_saltado_corta_la_racha_actual_pero_no_la_maxima() -> None:
    cumplidos = {hace(6), hace(5), hace(4), hace(3), hace(1), HOY}  # falta hace(2)

    assert calcular_racha(cumplidos, HOY) == Racha(actual=2, maxima=4)


def test_la_racha_cruza_el_cambio_de_mes() -> None:
    uno_de_marzo = date(2026, 3, 1)
    cumplidos = {date(2026, 2, 27), date(2026, 2, 28), uno_de_marzo}

    assert calcular_racha(cumplidos, uno_de_marzo) == Racha(actual=3, maxima=3)


def test_los_dias_posteriores_a_hoy_no_cuentan() -> None:
    futuro = {HOY + timedelta(days=1), HOY + timedelta(days=2)}

    assert calcular_racha({HOY} | futuro, HOY) == Racha(actual=1, maxima=1)


# --- Cumplimiento --------------------------------------------------------------------------


def test_cumplimiento_cuenta_la_ventana_que_termina_hoy() -> None:
    cumplidos = {HOY, hace(1), hace(6), hace(7), hace(29), hace(30)}

    assert cumplimiento(cumplidos, HOY, 7) == Cumplimiento(cumplidos=3, dias=7)
    assert cumplimiento(cumplidos, HOY, 30) == Cumplimiento(cumplidos=5, dias=30)
    assert cumplimiento(cumplidos, HOY, 7).porcentaje == 42.9


# --- Qué es un día cumplido ----------------------------------------------------------------


def test_un_habito_solo_cumple_los_dias_en_true() -> None:
    leer = MetricDefinition(nombre="leer", unidad="", tipo=TipoMetrica.BOOLEANA)

    cumplidos = dias_cumplidos(leer, entradas(leer, {hace(1): True, HOY: False}))

    assert cumplidos == {hace(1)}


def test_con_objetivo_cumple_al_alcanzarlo_sumando_las_lecturas_del_dia() -> None:
    pasos = MetricDefinition(
        nombre="pasos",
        unidad="pasos",
        tipo=TipoMetrica.CONTEO,
        agregacion=Agregacion.SUMA,
        on_duplicate=PoliticaDuplicado.KEEP_ALL,
        objetivo=8000,
    )
    lecturas = [
        pasos.crear_entrada(5000, timestamp=AHORA, logical_date=HOY, slot=0),
        pasos.crear_entrada(3000, timestamp=AHORA, logical_date=HOY, slot=1),
        pasos.crear_entrada(7999, timestamp=AHORA, logical_date=hace(1)),
    ]

    assert dias_cumplidos(pasos, lecturas) == {HOY}


def test_sin_objetivo_basta_con_registrar() -> None:
    peso = MetricDefinition(nombre="peso", unidad="kg", tipo=TipoMetrica.NUMERICA)
    ocio = MetricDefinition(
        nombre="ocio", unidad="", tipo=TipoMetrica.CATEGORICA, categorias=("leer", "jugar")
    )

    assert dias_cumplidos(peso, entradas(peso, {HOY: 74.3, hace(2): 75.0})) == {HOY, hace(2)}
    assert dias_cumplidos(ocio, entradas(ocio, {hace(1): "jugar"})) == {hace(1)}


# --- Caso de uso (memoria y SQL) -----------------------------------------------------------


def test_racha_de_un_habito_con_dia_saltado_y_hoy_sin_registrar(casos: CasosUsoTracking) -> None:
    casos.crear_metrica("leer", "", TipoMetrica.BOOLEANA)
    for dias, hecho in [(5, True), (4, True), (3, False), (2, True), (1, True)]:
        casos.registrar_metrica("leer", hecho, hace(dias))

    resumen = casos.racha("leer", HOY)

    assert resumen.metrica == "leer"
    assert resumen.racha == Racha(actual=2, maxima=2)
    assert resumen.semanal == Cumplimiento(cumplidos=4, dias=7)
    assert resumen.mensual == Cumplimiento(cumplidos=4, dias=30)


def test_racha_ignora_lo_registrado_despues_de_hoy(casos: CasosUsoTracking) -> None:
    casos.crear_metrica("leer", "", TipoMetrica.BOOLEANA)
    casos.registrar_metrica("leer", True, HOY)

    assert casos.racha("leer", hace(1)).racha == Racha(actual=0, maxima=0)


def test_racha_de_metrica_inexistente_falla(casos: CasosUsoTracking) -> None:
    with pytest.raises(MetricaNoEncontrada):
        casos.racha("nada", HOY)


# --- Métricas activas ----------------------------------------------------------------------


def test_desactivar_una_metrica_la_oculta_pero_conserva_sus_entradas(
    casos: CasosUsoTracking,
) -> None:
    casos.crear_metrica("peso", "kg", TipoMetrica.NUMERICA)
    casos.crear_metrica("leer", "", TipoMetrica.BOOLEANA)
    casos.registrar_metrica("leer", True, HOY)

    desactivada = casos.activar_metrica("leer", False)

    assert desactivada.activa is False
    assert [m.nombre for m in casos.listar_metricas(solo_activas=True)] == ["peso"]
    assert [m.nombre for m in casos.listar_metricas()] == ["leer", "peso"]
    assert [e.valor for e in casos.listar_entradas("leer", HOY, HOY)] == [True]

    assert casos.activar_metrica("leer", True).activa is True
    assert len(casos.listar_metricas(solo_activas=True)) == 2


def test_activar_una_metrica_inexistente_falla(casos: CasosUsoTracking) -> None:
    with pytest.raises(MetricaNoEncontrada):
        casos.activar_metrica("nada", False)
