from __future__ import annotations

from datetime import date

from agent.esquemas import argumentos
from core.herramientas import validar
from modules.training.application.casos_uso import CasosUsoTraining
from modules.training.application.herramientas import EjercicioSimple, herramientas_training


def test_registrar_entreno_con_records_y_listar(casos: CasosUsoTraining):
    h = {t.nombre: validar(t) for t in herramientas_training(casos)}
    registrar, entrenos = h["registrar_entreno"].funcion, h["entrenos"].funcion

    assert registrar(date(2026, 11, 10), "fuerza", [EjercicioSimple("press banca", 3, 8, 60)]) == (
        "Entreno de fuerza guardado (1440 kg)."
    )
    segundo = registrar(date(2026, 11, 12), "fuerza", [EjercicioSimple("press banca", 3, 8, 62.5)])
    assert "Récord de peso en press banca: 62.5 (antes 60)." in segundo
    assert registrar(date(2026, 11, 13), "correr", duracion_min=30).startswith("Entreno de correr")

    assert entrenos(date(2026, 11, 1), date(2026, 11, 30)).splitlines() == [
        "- 10/11/2026 fuerza: press banca 3x8x60",
        "- 12/11/2026 fuerza: press banca 3x8x62.5",
        "- 13/11/2026 correr",
    ]


def test_los_ejercicios_llegan_del_llm_como_json(casos: CasosUsoTraining):
    (tool,) = [t for t in herramientas_training(casos) if t.nombre == "registrar_entreno"]
    kwargs = argumentos(
        validar(tool),
        {
            "fecha": "2026-11-14",
            "tipo": "fuerza",
            "ejercicios": [{"nombre": "dominadas", "series": 3, "reps": 10}],
        },
    )
    assert kwargs["ejercicios"] == [EjercicioSimple("dominadas", 3, 10, 0.0)]
    assert tool.funcion(**kwargs) == "Entreno de fuerza guardado (0 kg)."
