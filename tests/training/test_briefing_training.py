from __future__ import annotations

from datetime import date

from modules.training.application.briefing import SeccionBriefingTraining
from modules.training.application.casos_uso import CasosUsoTraining

SABADO = date(2026, 11, 14)


def test_ultimo_entreno_y_sesiones_de_la_semana(casos: CasosUsoTraining):
    casos.registrar_sesion(date(2026, 11, 6), "correr")  # semana anterior
    casos.registrar_sesion(date(2026, 11, 10), "fuerza")
    casos.registrar_sesion(date(2026, 11, 12), "fuerza")

    assert SeccionBriefingTraining(casos).lineas(SABADO) == [
        "Último entreno: fuerza, hace 2 días",
        "Esta semana: 2 sesiones",
    ]


def test_hoy_y_una_sola_sesion(casos: CasosUsoTraining):
    casos.registrar_sesion(SABADO, "correr")
    assert SeccionBriefingTraining(casos).lineas(SABADO) == [
        "Último entreno: correr, hoy",
        "Esta semana: 1 sesión",
    ]


def test_sin_entrenos_recientes(casos: CasosUsoTraining):
    casos.registrar_sesion(date(2026, 10, 1), "fuerza")
    assert SeccionBriefingTraining(casos).lineas(SABADO) == [
        "Ningún entreno en los últimos 14 días."
    ]
