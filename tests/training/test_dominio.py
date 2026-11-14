from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from modules.training.domain.errores import EjercicioInvalido, SerieInvalida, SesionInvalida
from modules.training.domain.progreso import (
    Marca,
    PuntoProgreso,
    RecordBatido,
    TipoRecord,
    lunes_de,
    progreso,
    records_batidos,
    records_personales,
    volumen_por_semana,
)
from modules.training.domain.sesiones import Ejercicio, Serie, Sesion, un_rm_epley

AHORA = datetime(2026, 11, 14, 19, 0, tzinfo=UTC)
D10, D12, D14 = date(2026, 11, 10), date(2026, 11, 12), date(2026, 11, 14)


def ejercicio(nombre: str, *series: tuple[int, float]) -> Ejercicio:
    return Ejercicio(nombre=nombre, series=tuple(Serie(reps=r, peso=p) for r, p in series))


def sesion(dia: date, *ejercicios: Ejercicio) -> Sesion:
    return Sesion(logical_date=dia, tipo="fuerza", timestamp=AHORA, ejercicios=ejercicios)


# --- 1RM estimado --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("peso", "reps", "esperado"),
    [
        (100, 1, 100.0),  # una repetición: el 1RM es el propio peso
        (100, 10, 133.33),
        (60, 8, 76.0),
        (0, 12, 0.0),  # peso corporal: sin carga no hay 1RM
    ],
)
def test_1rm_de_epley(peso: float, reps: int, esperado: float) -> None:
    assert un_rm_epley(peso, reps) == pytest.approx(esperado, abs=0.01)
    assert Serie(reps=reps, peso=peso).un_rm == pytest.approx(esperado, abs=0.01)


def test_el_1rm_de_un_ejercicio_es_el_de_su_mejor_serie() -> None:
    banca = ejercicio("press banca", (8, 60), (3, 75), (10, 50))

    assert banca.un_rm == pytest.approx(82.5)  # 3 x 75
    assert banca.peso_maximo == 75


# --- Volumen -------------------------------------------------------------------------------


def test_volumen_de_serie_ejercicio_y_sesion() -> None:
    banca = ejercicio("press banca", (8, 60), (6, 65))
    dominadas = ejercicio("dominadas", (10, 0))
    entreno = sesion(D14, banca, dominadas)

    assert Serie(reps=8, peso=60).volumen == 480
    assert banca.volumen == 870
    assert dominadas.volumen == 0
    assert entreno.volumen == 870
    assert sesion(D14).volumen == 0  # una sesión de cardio no tiene ejercicios


def test_volumen_por_semana_agrupa_por_lunes() -> None:
    sesiones = [
        sesion(date(2026, 11, 9), ejercicio("sentadilla", (5, 100))),  # lunes
        sesion(date(2026, 11, 15), ejercicio("sentadilla", (5, 100))),  # domingo, misma semana
        sesion(date(2026, 11, 16), ejercicio("sentadilla", (5, 80))),  # lunes siguiente
    ]

    assert volumen_por_semana(sesiones) == [
        (date(2026, 11, 9), 1000.0),
        (date(2026, 11, 16), 400.0),
    ]
    assert lunes_de(date(2026, 11, 14)) == date(2026, 11, 9)


# --- Progreso y récords --------------------------------------------------------------------


def test_progreso_da_un_punto_por_dia_solo_del_ejercicio_pedido() -> None:
    sesiones = [
        sesion(D12, ejercicio("press banca", (5, 70)), ejercicio("sentadilla", (5, 100))),
        sesion(D10, ejercicio("press banca", (8, 60), (8, 60))),
        sesion(D12, ejercicio("Press  Banca", (10, 50))),  # segunda sesión del mismo día
    ]

    puntos = progreso(sesiones, "PRESS BANCA")

    assert puntos == [
        PuntoProgreso(logical_date=D10, un_rm=pytest.approx(76.0), peso_maximo=60, volumen=960),
        PuntoProgreso(
            logical_date=D12, un_rm=pytest.approx(81.67, abs=0.01), peso_maximo=70, volumen=850
        ),
    ]
    assert progreso(sesiones, "peso muerto") == []


def test_records_personales_por_ejercicio() -> None:
    sesiones = [
        sesion(D10, ejercicio("press banca", (8, 60), (8, 60), (8, 60))),  # más volumen
        sesion(D12, ejercicio("press banca", (3, 75))),  # más peso y más 1RM
        sesion(D14, ejercicio("press banca", (3, 75))),  # empata: gana el primer día
        sesion(D14, ejercicio("sentadilla", (5, 100))),
    ]

    banca, sentadilla = records_personales(sesiones)

    assert banca.ejercicio == "press banca"
    assert banca.peso == Marca(valor=75, logical_date=D12)
    assert banca.un_rm == Marca(valor=pytest.approx(82.5), logical_date=D12)
    assert banca.volumen == Marca(valor=1440, logical_date=D10)
    assert sentadilla.peso == Marca(valor=100, logical_date=D14)


def test_records_batidos_solo_los_que_superan_la_marca_anterior() -> None:
    anteriores = [sesion(D10, ejercicio("press banca", (8, 60), (8, 60)))]
    nueva = sesion(D12, ejercicio("press banca", (5, 70)), ejercicio("sentadilla", (5, 100)))

    batidos = records_batidos(nueva, anteriores)

    # 5x70: más peso (70 > 60) y más 1RM (81,7 > 76), pero menos volumen (350 < 960).
    # La sentadilla es nueva: no hay marca previa que batir.
    assert batidos == [
        RecordBatido(ejercicio="press banca", tipo=TipoRecord.PESO, valor=70, anterior=60),
        RecordBatido(
            ejercicio="press banca",
            tipo=TipoRecord.UN_RM,
            valor=pytest.approx(81.67, abs=0.01),
            anterior=pytest.approx(76.0),
        ),
    ]
    assert (
        records_batidos(sesion(D14, ejercicio("press banca", (5, 70))), [*anteriores, nueva]) == []
    )


# --- Validación ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "datos",
    [
        {"reps": 0, "peso": 60},
        {"reps": -3, "peso": 60},
        {"reps": 8.5, "peso": 60},
        {"reps": True, "peso": 60},
        {"reps": 8, "peso": -1},
        {"reps": 8, "peso": float("nan")},
        {"reps": 8, "peso": 60, "rpe": 0.5},
        {"reps": 8, "peso": 60, "rpe": 11},
    ],
)
def test_serie_invalida(datos: dict[str, float]) -> None:
    with pytest.raises(SerieInvalida):
        Serie(**datos)  # type: ignore[arg-type]


def test_serie_admite_peso_cero_y_rpe_con_medios() -> None:
    assert Serie(reps=12, peso=0, rpe=8.5).rpe == 8.5


def test_ejercicio_normaliza_el_nombre_y_exige_series() -> None:
    assert ejercicio("  Press   BANCA ", (8, 60)).nombre == "press banca"
    with pytest.raises(EjercicioInvalido):
        Ejercicio(nombre="   ", series=(Serie(reps=8, peso=60),))
    with pytest.raises(EjercicioInvalido):
        Ejercicio(nombre="press banca", series=())


@pytest.mark.parametrize(
    "cambios",
    [
        {"tipo": "  "},
        {"duracion_min": 0},
        {"duracion_min": 45.5},
        {"energia_previa": 0},
        {"energia_previa": 11},
        {"timestamp": datetime(2026, 11, 14, 19, 0)},  # sin zona
    ],
)
def test_sesion_invalida(cambios: dict[str, object]) -> None:
    datos = {"logical_date": D14, "tipo": "fuerza", "timestamp": AHORA, **cambios}

    with pytest.raises(SesionInvalida):
        Sesion(**datos)  # type: ignore[arg-type]


def test_sesion_normaliza_el_tipo_y_acepta_opcionales_vacios() -> None:
    entreno = Sesion(logical_date=D14, tipo="  Pierna ", timestamp=AHORA)

    assert (entreno.tipo, entreno.duracion_min, entreno.energia_previa) == ("pierna", None, None)
