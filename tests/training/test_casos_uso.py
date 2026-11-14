from __future__ import annotations

from datetime import date

import pytest

from core.contracts import SeriesProvider
from modules.training.application.casos_uso import CasosUsoTraining
from modules.training.application.series import ProveedorSeriesTraining
from modules.training.domain.errores import (
    EjercicioNoEncontrado,
    SerieInvalida,
    SerieTemporalNoEncontrada,
    SesionNoEncontrada,
)
from modules.training.domain.progreso import TipoRecord
from modules.training.domain.sesiones import Ejercicio, Serie, Sesion
from tests.training.conftest import AHORA, D10, D12, D14, ejercicio


def test_registrar_y_listar_conserva_la_sesion_completa(casos: CasosUsoTraining) -> None:
    banca = Ejercicio(
        nombre="Press banca", series=(Serie(reps=8, peso=60, rpe=7.5), Serie(reps=6, peso=65))
    )
    guardada = casos.registrar_sesion(
        D14, "Fuerza", [banca, ejercicio("dominadas", (10, 0))], duracion_min=55, energia_previa=7
    )

    (leida,) = casos.listar_sesiones(D14, D14)

    assert leida == guardada.sesion
    assert (leida.tipo, leida.duracion_min, leida.energia_previa) == ("fuerza", 55, 7)
    assert leida.timestamp == AHORA
    assert [e.nombre for e in leida.ejercicios] == ["press banca", "dominadas"]
    assert leida.ejercicios[0].series == (Serie(reps=8, peso=60, rpe=7.5), Serie(reps=6, peso=65))
    assert leida.volumen == 870


def test_listar_filtra_y_ordena_por_fecha(casos: CasosUsoTraining) -> None:
    for dia in (D14, D10, D12):
        casos.registrar_sesion(dia, "cardio", duracion_min=30)

    assert [s.logical_date for s in casos.listar_sesiones(date.min, date.max)] == [D10, D12, D14]
    assert [s.logical_date for s in casos.listar_sesiones(D12, D12)] == [D12]


def test_una_sesion_invalida_no_se_guarda(casos: CasosUsoTraining) -> None:
    with pytest.raises(SerieInvalida):
        casos.registrar_sesion(D14, "fuerza", [ejercicio("press banca", (0, 60))])

    assert casos.listar_sesiones(date.min, date.max) == []


def test_registrar_avisa_de_los_records_batidos(casos: CasosUsoTraining) -> None:
    primera = casos.registrar_sesion(D10, "fuerza", [ejercicio("press banca", (8, 60))])
    segunda = casos.registrar_sesion(D12, "fuerza", [ejercicio("press banca", (8, 62.5))])
    # Una sesión antigua metida después solo se compara con las anteriores a su fecha.
    atrasada = casos.registrar_sesion(D10, "fuerza", [ejercicio("press banca", (8, 61))])

    assert primera.records == []
    assert {r.tipo for r in segunda.records} == {
        TipoRecord.PESO,
        TipoRecord.UN_RM,
        TipoRecord.VOLUMEN,
    }
    assert [(r.valor, r.anterior) for r in segunda.records if r.tipo is TipoRecord.PESO] == [
        (62.5, 60)
    ]
    assert {r.tipo for r in atrasada.records} == {
        TipoRecord.PESO,
        TipoRecord.UN_RM,
        TipoRecord.VOLUMEN,
    }


def test_borrar_sesion(casos: CasosUsoTraining) -> None:
    guardada = casos.registrar_sesion(D14, "fuerza", [ejercicio("press banca", (8, 60))])

    casos.borrar_sesion(guardada.sesion.id)

    assert casos.listar_sesiones(date.min, date.max) == []
    assert casos.listar_ejercicios() == []
    with pytest.raises(SesionNoEncontrada):
        casos.borrar_sesion(guardada.sesion.id)


def test_progreso_y_records_de_un_ejercicio(casos: CasosUsoTraining) -> None:
    casos.registrar_sesion(D10, "fuerza", [ejercicio("press banca", (8, 60))])
    casos.registrar_sesion(
        D14, "fuerza", [ejercicio("press banca", (5, 70)), ejercicio("sentadilla", (5, 100))]
    )

    puntos = casos.progreso_ejercicio("Press Banca", D10, D14)

    assert casos.listar_ejercicios() == ["press banca", "sentadilla"]
    assert [(p.logical_date, p.peso_maximo) for p in puntos] == [(D10, 60), (D14, 70)]
    assert [round(p.un_rm, 2) for p in puntos] == [76.0, 81.67]
    assert casos.progreso_ejercicio("press banca", D12, D12) == []
    banca, _sentadilla = casos.records()
    assert (banca.peso.valor, banca.peso.logical_date) == (70, D14)
    with pytest.raises(EjercicioNoEncontrado):
        casos.progreso_ejercicio("peso muerto", D10, D14)


def test_volumen_semanal_cuenta_semanas_completas(casos: CasosUsoTraining) -> None:
    lunes, domingo = date(2026, 11, 9), date(2026, 11, 15)
    casos.registrar_sesion(lunes, "fuerza", [ejercicio("sentadilla", (5, 100))])
    casos.registrar_sesion(domingo, "fuerza", [ejercicio("sentadilla", (5, 100))])
    casos.registrar_sesion(date(2026, 11, 18), "fuerza", [ejercicio("sentadilla", (5, 80))])

    assert casos.volumen_semanal(date.min, date.max) == [
        (lunes, 1000.0),
        (date(2026, 11, 16), 400.0),
    ]
    # Aunque `hasta` caiga a mitad de semana, la semana sale entera.
    assert casos.volumen_semanal(lunes, date(2026, 11, 11)) == [(lunes, 1000.0)]
    # Una semana cuyo lunes queda fuera del rango no sale a medias.
    assert casos.volumen_semanal(date(2026, 11, 10), domingo) == []
    assert casos.volumen_semanal(domingo, lunes) == []


def test_eventos_al_registrar_y_al_borrar(repo: object) -> None:
    registradas: list[Sesion] = []
    borradas: list[str] = []
    casos = CasosUsoTraining(
        repo,  # type: ignore[arg-type]
        reloj=lambda: AHORA,
        al_registrar=registradas.append,
        al_borrar=borradas.append,
    )

    guardada = casos.registrar_sesion(D14, "cardio")
    with pytest.raises(SerieInvalida):
        casos.registrar_sesion(D14, "fuerza", [ejercicio("press banca", (0, 60))])
    casos.borrar_sesion(guardada.sesion.id)

    assert registradas == [guardada.sesion]
    assert borradas == [guardada.sesion.id]


# --- Proveedor de series -------------------------------------------------------------------


def test_series_de_volumen_semanal_y_1rm_por_ejercicio(casos: CasosUsoTraining) -> None:
    proveedor = ProveedorSeriesTraining(casos)
    casos.registrar_sesion(D10, "fuerza", [ejercicio("press banca", (8, 60))])
    casos.registrar_sesion(D14, "fuerza", [ejercicio("press banca", (5, 70))])

    assert isinstance(proveedor, SeriesProvider)
    assert [(s.nombre, s.unidad) for s in proveedor.list_series()] == [
        ("volumen_semanal", "kg"),
        ("1rm press banca", "kg"),
    ]
    assert proveedor.get_series("volumen_semanal", date(2026, 11, 1), date(2026, 11, 30)) == [
        (date(2026, 11, 9), 830.0)
    ]
    puntos = proveedor.get_series("1rm press banca", D10, D14)
    assert [(dia, round(valor, 2)) for dia, valor in puntos] == [(D10, 76.0), (D14, 81.67)]
    assert proveedor.get_series("1rm press banca", D12, D12) == []
    for desconocida in ("1rm peso muerto", "peso"):
        with pytest.raises(SerieTemporalNoEncontrada):
            proveedor.get_series(desconocida, D10, D14)
