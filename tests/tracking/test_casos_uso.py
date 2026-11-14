from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from modules.tracking.application.casos_uso import CasosUsoTracking
from modules.tracking.application.ports import RepositorioEntradas, RepositorioMetricas
from modules.tracking.domain.errores import (
    EntradaNoEncontrada,
    MetricaDuplicada,
    MetricaNoEncontrada,
    ValorFueraDeRango,
)
from modules.tracking.domain.metricas import (
    Agregacion,
    MetricDefinition,
    MetricEntry,
    PoliticaDuplicado,
    TipoMetrica,
)

HOY = date(2026, 11, 14)
AYER = date(2026, 11, 13)


def crear_peso(casos: CasosUsoTracking) -> MetricDefinition:
    return casos.crear_metrica(
        "peso", "kg", TipoMetrica.NUMERICA, agregacion=Agregacion.MEDIA, minimo=20, maximo=300
    )


def crear_cafes(casos: CasosUsoTracking) -> MetricDefinition:
    return casos.crear_metrica(
        "cafes",
        "tazas",
        TipoMetrica.CONTEO,
        agregacion=Agregacion.SUMA,
        on_duplicate=PoliticaDuplicado.KEEP_ALL,
    )


def test_crear_y_listar_metricas_por_orden_alfabetico(casos: CasosUsoTracking) -> None:
    crear_peso(casos)
    crear_cafes(casos)

    assert [m.nombre for m in casos.listar_metricas()] == ["cafes", "peso"]


def test_la_metrica_se_recupera_con_toda_su_configuracion(casos: CasosUsoTracking) -> None:
    creada = casos.crear_metrica(
        "ocio", "", TipoMetrica.CATEGORICA, categorias=("leer", "jugar", "series")
    )
    crear_peso(casos)

    ocio, peso = casos.listar_metricas()

    assert ocio == creada
    assert (peso.minimo, peso.maximo, peso.agregacion) == (20, 300, Agregacion.MEDIA)


def test_crear_metrica_repetida_falla(casos: CasosUsoTracking) -> None:
    crear_peso(casos)

    with pytest.raises(MetricaDuplicada):
        crear_peso(casos)


def test_registrar_en_metrica_inexistente_falla(casos: CasosUsoTracking) -> None:
    with pytest.raises(MetricaNoEncontrada):
        casos.registrar_metrica("altura", 180, HOY)


def test_registrar_valida_el_valor(casos: CasosUsoTracking) -> None:
    crear_peso(casos)

    with pytest.raises(ValorFueraDeRango):
        casos.registrar_metrica("peso", 5, HOY)
    assert casos.listar_entradas("peso", HOY, HOY) == []


def test_segundo_peso_del_dia_sobrescribe(casos: CasosUsoTracking) -> None:
    crear_peso(casos)
    primera = casos.registrar_metrica("peso", 74.3, HOY)
    despues = datetime(2026, 11, 14, 20, 0, tzinfo=UTC)

    segunda = casos.registrar_metrica("peso", 74.0, HOY, timestamp=despues)

    entradas = casos.listar_entradas("peso", HOY, HOY)
    assert [(e.valor, e.slot, e.timestamp) for e in entradas] == [(74.0, 0, despues)]
    assert segunda.id == primera.id == entradas[0].id


def test_con_keep_all_se_guardan_las_dos(casos: CasosUsoTracking) -> None:
    crear_cafes(casos)

    casos.registrar_metrica("cafes", 1, HOY)
    casos.registrar_metrica("cafes", 2, HOY)

    entradas = casos.listar_entradas("cafes", HOY, HOY)
    assert [(e.valor, e.slot) for e in entradas] == [(1, 0), (2, 1)]


def test_replace_no_pisa_otros_dias_ni_otras_metricas(casos: CasosUsoTracking) -> None:
    crear_peso(casos)
    crear_cafes(casos)
    casos.registrar_metrica("peso", 75.0, AYER)
    casos.registrar_metrica("peso", 74.3, HOY)
    casos.registrar_metrica("cafes", 2, HOY)

    assert [e.valor for e in casos.listar_entradas("peso", AYER, HOY)] == [75.0, 74.3]
    assert [e.valor for e in casos.listar_entradas("cafes", AYER, HOY)] == [2]


def test_listar_filtra_por_rango_con_extremos_incluidos(casos: CasosUsoTracking) -> None:
    crear_peso(casos)
    for dia, valor in [(10, 76.0), (12, 75.5), (14, 75.0)]:
        casos.registrar_metrica("peso", valor, date(2026, 11, dia))

    entradas = casos.listar_entradas("peso", date(2026, 11, 12), date(2026, 11, 14))

    assert [e.logical_date.day for e in entradas] == [12, 14]


def test_los_valores_conservan_su_tipo(casos: CasosUsoTracking) -> None:
    casos.crear_metrica("leer", "", TipoMetrica.BOOLEANA)
    casos.crear_metrica("animo", "", TipoMetrica.ESCALA, escala_max=10)
    casos.crear_metrica("ocio", "", TipoMetrica.CATEGORICA, categorias=("leer", "jugar"))
    casos.registrar_metrica("leer", True, HOY)
    casos.registrar_metrica("animo", 7, HOY)
    casos.registrar_metrica("ocio", "jugar", HOY)

    def valor(nombre: str) -> object:
        return casos.listar_entradas(nombre, HOY, HOY)[0].valor

    assert valor("leer") is True
    assert valor("animo") == 7 and isinstance(valor("animo"), int)
    assert valor("ocio") == "jugar"


def test_borrar_entrada(casos: CasosUsoTracking) -> None:
    crear_peso(casos)
    entrada = casos.registrar_metrica("peso", 74.3, HOY)

    casos.borrar_entrada(entrada.id)

    assert casos.listar_entradas("peso", HOY, HOY) == []
    with pytest.raises(EntradaNoEncontrada):
        casos.borrar_entrada(entrada.id)


def test_tras_borrar_keep_all_no_reutiliza_un_slot_ocupado(casos: CasosUsoTracking) -> None:
    crear_cafes(casos)
    primera = casos.registrar_metrica("cafes", 1, HOY)
    casos.registrar_metrica("cafes", 2, HOY)
    casos.borrar_entrada(primera.id)

    casos.registrar_metrica("cafes", 3, HOY)

    assert [(e.valor, e.slot) for e in casos.listar_entradas("cafes", HOY, HOY)] == [(2, 1), (3, 2)]


def test_al_registrar_avisa_con_la_entrada_guardada(
    repos: tuple[RepositorioMetricas, RepositorioEntradas],
) -> None:
    avisos: list[tuple[MetricDefinition, MetricEntry]] = []
    metricas, entradas = repos
    casos = CasosUsoTracking(
        metricas,
        entradas,
        al_registrar=lambda d, e: avisos.append((d, e)),
    )
    peso = crear_peso(casos)

    entrada = casos.registrar_metrica("peso", 74.3, HOY)

    assert avisos == [(peso, entrada)]
    assert entrada.timestamp.tzinfo is not None
