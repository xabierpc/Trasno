from __future__ import annotations

from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

import pytest

from modules.tracking.domain.errores import (
    CategoriaDesconocida,
    DefinicionInvalida,
    EntradaInvalida,
    TipoIncorrecto,
    ValorFueraDeRango,
)
from modules.tracking.domain.fecha_logica import es_madrugada, opciones_fecha_logica
from modules.tracking.domain.metricas import (
    Agregacion,
    MetricDefinition,
    MetricEntry,
    PoliticaDuplicado,
    TipoMetrica,
)

MADRID = ZoneInfo("Europe/Madrid")
AHORA = datetime(2026, 11, 14, 9, 30, tzinfo=MADRID)
HOY = date(2026, 11, 14)


def definicion(tipo: TipoMetrica, **extra: object) -> MetricDefinition:
    return MetricDefinition(nombre="prueba", unidad="u", tipo=tipo, **extra)


# --- Definiciones válidas de los 6 tipos -------------------------------------------------


def test_definiciones_validas_de_los_seis_tipos() -> None:
    peso = MetricDefinition(
        nombre="peso",
        unidad="kg",
        tipo=TipoMetrica.NUMERICA,
        agregacion=Agregacion.MEDIA,
        minimo=20,
        maximo=300,
    )
    sueno = MetricDefinition(nombre="sueño", unidad="min", tipo=TipoMetrica.DURACION)
    leer = MetricDefinition(nombre="leer", unidad="", tipo=TipoMetrica.BOOLEANA)
    animo = MetricDefinition(nombre="ánimo", unidad="", tipo=TipoMetrica.ESCALA, escala_max=10)
    cafes = MetricDefinition(
        nombre="cafés",
        unidad="tazas",
        tipo=TipoMetrica.CONTEO,
        agregacion=Agregacion.SUMA,
        on_duplicate=PoliticaDuplicado.KEEP_ALL,
    )
    ocio = MetricDefinition(
        nombre="ocio",
        unidad="",
        tipo=TipoMetrica.CATEGORICA,
        categorias=("leer", "videojuegos"),
    )

    assert {d.tipo for d in (peso, sueno, leer, animo, cafes, ocio)} == set(TipoMetrica)
    assert peso.on_duplicate is PoliticaDuplicado.REPLACE
    assert cafes.on_duplicate is PoliticaDuplicado.KEEP_ALL
    assert peso.id != sueno.id


# --- Valores válidos ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("tipo", "extra", "valor", "esperado"),
    [
        (TipoMetrica.NUMERICA, {}, 74.3, 74.3),
        (TipoMetrica.NUMERICA, {}, 74, 74.0),
        (TipoMetrica.DURACION, {}, 450, 450),
        (TipoMetrica.BOOLEANA, {}, True, True),
        (TipoMetrica.ESCALA, {"escala_max": 10}, 7, 7),
        (TipoMetrica.CONTEO, {}, 0, 0),
        (TipoMetrica.CATEGORICA, {"categorias": ("leer", "cine")}, "cine", "cine"),
    ],
)
def test_valor_valido_se_normaliza(
    tipo: TipoMetrica, extra: dict[str, object], valor: object, esperado: object
) -> None:
    resultado = definicion(tipo, **extra).validar(valor)
    assert resultado == esperado
    assert type(resultado) is type(esperado)


# --- Valores inválidos -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("tipo", "extra", "valor"),
    [
        (TipoMetrica.NUMERICA, {}, "74"),
        (TipoMetrica.NUMERICA, {}, True),
        (TipoMetrica.DURACION, {}, 7.5),
        (TipoMetrica.BOOLEANA, {}, 3),
        (TipoMetrica.BOOLEANA, {}, 1),
        (TipoMetrica.ESCALA, {"escala_max": 10}, 7.5),
        (TipoMetrica.CONTEO, {}, 2.5),
        (TipoMetrica.CONTEO, {}, False),
        (TipoMetrica.CATEGORICA, {"categorias": ("leer",)}, 1),
    ],
)
def test_tipo_incorrecto(tipo: TipoMetrica, extra: dict[str, object], valor: object) -> None:
    with pytest.raises(TipoIncorrecto):
        definicion(tipo, **extra).validar(valor)


@pytest.mark.parametrize(
    ("tipo", "extra", "valor"),
    [
        (TipoMetrica.NUMERICA, {"minimo": 20, "maximo": 300}, 19.9),
        (TipoMetrica.NUMERICA, {"minimo": 20, "maximo": 300}, 301),
        (TipoMetrica.NUMERICA, {}, float("nan")),
        (TipoMetrica.NUMERICA, {}, float("inf")),
        (TipoMetrica.DURACION, {}, -1),
        (TipoMetrica.ESCALA, {"escala_max": 10}, 0),
        (TipoMetrica.ESCALA, {"escala_max": 10}, 11),
        (TipoMetrica.CONTEO, {}, -1),
        (TipoMetrica.CONTEO, {"maximo": 10}, 11),
    ],
)
def test_valor_fuera_de_rango(tipo: TipoMetrica, extra: dict[str, object], valor: object) -> None:
    with pytest.raises(ValorFueraDeRango):
        definicion(tipo, **extra).validar(valor)


def test_categoria_desconocida() -> None:
    ocio = definicion(TipoMetrica.CATEGORICA, categorias=("leer", "cine"))
    with pytest.raises(CategoriaDesconocida):
        ocio.validar("teatro")


def test_los_errores_de_valor_comparten_base() -> None:
    from modules.tracking.domain.errores import ErrorTracking, ValorInvalido

    for error in (TipoIncorrecto, ValorFueraDeRango, CategoriaDesconocida):
        assert issubclass(error, ValorInvalido)
        assert issubclass(error, ErrorTracking)


# --- Definiciones mal hechas -------------------------------------------------------------


@pytest.mark.parametrize(
    ("tipo", "extra"),
    [
        (TipoMetrica.ESCALA, {}),
        (TipoMetrica.ESCALA, {"escala_max": 1}),
        (TipoMetrica.NUMERICA, {"escala_max": 10}),
        (TipoMetrica.CATEGORICA, {}),
        (TipoMetrica.CATEGORICA, {"categorias": ("leer", "leer")}),
        (TipoMetrica.CATEGORICA, {"categorias": ("leer", " ")}),
        (TipoMetrica.NUMERICA, {"categorias": ("leer",)}),
        (TipoMetrica.NUMERICA, {"minimo": 10, "maximo": 5}),
        (TipoMetrica.BOOLEANA, {"minimo": 0}),
        (TipoMetrica.ESCALA, {"escala_max": 10, "maximo": 5}),
        (TipoMetrica.CATEGORICA, {"categorias": ("leer",), "objetivo": 3}),
    ],
)
def test_definicion_invalida(tipo: TipoMetrica, extra: dict[str, object]) -> None:
    with pytest.raises(DefinicionInvalida):
        definicion(tipo, **extra)


def test_nombre_vacio_es_invalido() -> None:
    with pytest.raises(DefinicionInvalida):
        MetricDefinition(nombre="  ", unidad="kg", tipo=TipoMetrica.NUMERICA)


def test_categoria_suma_o_media_no_tiene_sentido() -> None:
    with pytest.raises(DefinicionInvalida):
        definicion(TipoMetrica.CATEGORICA, categorias=("leer",), agregacion=Agregacion.MEDIA)


# --- Entradas ----------------------------------------------------------------------------


def test_crear_entrada_valida_y_normaliza() -> None:
    peso = definicion(TipoMetrica.NUMERICA)
    entrada = peso.crear_entrada(74, timestamp=AHORA, logical_date=HOY)

    assert isinstance(entrada, MetricEntry)
    assert entrada.metric_id == peso.id
    assert entrada.valor == 74.0
    assert entrada.slot == 0
    assert entrada.logical_date == HOY


def test_crear_entrada_con_valor_invalido_falla() -> None:
    animo = definicion(TipoMetrica.ESCALA, escala_max=5)
    with pytest.raises(ValorFueraDeRango):
        animo.crear_entrada(6, timestamp=AHORA, logical_date=HOY)


def test_entrada_sin_zona_horaria_falla() -> None:
    peso = definicion(TipoMetrica.NUMERICA)
    with pytest.raises(EntradaInvalida):
        peso.crear_entrada(74, timestamp=datetime(2026, 11, 14, 9, 30), logical_date=HOY)


def test_entrada_con_slot_negativo_falla() -> None:
    peso = definicion(TipoMetrica.NUMERICA)
    with pytest.raises(EntradaInvalida):
        peso.crear_entrada(74, timestamp=AHORA, logical_date=HOY, slot=-1)


# --- Fecha lógica y madrugada ------------------------------------------------------------

VENTANA = (time(0, 0), time(6, 0))


@pytest.mark.parametrize(
    ("hora", "esperado"),
    [(time(0, 0), True), (time(0, 30), True), (time(5, 59), True), (time(6, 0), False)],
)
def test_es_madrugada_en_hora_local(hora: time, esperado: bool) -> None:
    instante = datetime.combine(HOY, hora, tzinfo=MADRID)
    assert es_madrugada(instante, VENTANA, "Europe/Madrid") is esperado


def test_es_madrugada_convierte_desde_utc() -> None:
    # 23:30 UTC del 13 son las 00:30 del 14 en Madrid (UTC+1 en noviembre).
    instante = datetime(2026, 11, 13, 23, 30, tzinfo=UTC)
    assert es_madrugada(instante, VENTANA, "Europe/Madrid") is True


def test_ventana_que_cruza_medianoche() -> None:
    ventana = (time(23, 0), time(5, 0))
    assert es_madrugada(datetime(2026, 11, 14, 23, 30, tzinfo=MADRID), ventana, MADRID)
    assert es_madrugada(datetime(2026, 11, 14, 4, 0, tzinfo=MADRID), ventana, MADRID)
    assert not es_madrugada(datetime(2026, 11, 14, 12, 0, tzinfo=MADRID), ventana, MADRID)


def test_opciones_fecha_logica_devuelve_ayer_y_hoy_locales() -> None:
    instante = datetime(2026, 11, 13, 23, 30, tzinfo=UTC)
    assert opciones_fecha_logica(instante, "Europe/Madrid") == (
        date(2026, 11, 13),
        date(2026, 11, 14),
    )


def test_madrugada_sin_zona_falla() -> None:
    with pytest.raises(EntradaInvalida):
        es_madrugada(datetime(2026, 11, 14, 1, 0), VENTANA, "Europe/Madrid")
