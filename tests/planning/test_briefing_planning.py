from __future__ import annotations

from datetime import date, time

from modules.planning.application.briefing import SeccionBriefingPlanning
from modules.planning.application.casos_uso import CasosUsoPlanning
from modules.planning.domain.tareas import Prioridad
from tests.planning.conftest import LUNES, a_las


def test_citas_tareas_pendientes_y_atrasadas(casos: CasosUsoPlanning):
    casos.crear_bloque("Cálculo", 0, time(9), time(11), lugar="A1")
    casos.crear_evento("Médico", a_las(12), a_las(13))
    casos.crear_tarea("estudiar", fecha=LUNES, prioridad=Prioridad.ALTA)
    hecha = casos.crear_tarea("hecha", fecha=LUNES)
    casos.completar_tarea(hecha.id)
    casos.crear_tarea("vieja 1", fecha=date(2026, 11, 10))
    casos.crear_tarea("vieja 2", fecha=date(2026, 11, 11))

    assert SeccionBriefingPlanning(casos).lineas(LUNES) == [
        "**09:00-11:00** Cálculo · A1",
        "**12:00-13:00** Médico",
        "Tarea: estudiar (prioridad alta)",
        "2 tareas atrasadas",
    ]


def test_dia_vacio(casos: CasosUsoPlanning):
    assert SeccionBriefingPlanning(casos).lineas(LUNES) == ["Sin citas ni tareas."]
