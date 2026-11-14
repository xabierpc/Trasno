from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, time

import pytest

from core.herramientas import validar
from modules.planning.application.casos_uso import CasosUsoPlanning
from modules.planning.application.herramientas import herramientas_planning
from modules.planning.domain.errores import TareaNoEncontrada
from modules.planning.domain.tareas import Prioridad
from tests.planning.conftest import LUNES, ZONA, a_las

Herramientas = dict[str, Callable[..., str]]


@pytest.fixture
def h(casos: CasosUsoPlanning) -> Herramientas:
    return {t.nombre: t.funcion for t in herramientas_planning(casos, ZONA)}


def test_todas_son_validas_y_las_que_cambian_cosas_piden_confirmacion(casos: CasosUsoPlanning):
    tools = {t.nombre: validar(t) for t in herramientas_planning(casos, ZONA)}
    confirmar = {n for n, t in tools.items() if t.requiere_confirmacion}
    assert confirmar == {"crear_tarea", "borrar_tarea", "crear_evento", "borrar_evento"}


def test_crear_y_completar_tarea_y_ver_la_agenda(h: Herramientas, casos: CasosUsoPlanning):
    creada = h["crear_tarea"]("estudiar cálculo", LUNES, Prioridad.ALTA)
    assert creada.startswith("Tarea creada para el 16/11/2026: estudiar cálculo [")
    (tarea,) = casos.agenda(LUNES).tareas

    assert h["completar_tarea"](tarea.id) == "Hecha: estudiar cálculo."
    agenda = h["agenda"](LUNES)
    assert agenda.splitlines() == [
        "Agenda del 16/11/2026:",
        "- Sin citas.",
        f"- Tarea [{tarea.id}] estudiar cálculo · alta · hecha",
    ]


def test_mover_y_borrar(h: Herramientas, casos: CasosUsoPlanning):
    tarea = casos.crear_tarea("x", fecha=LUNES)
    assert h["mover_tarea"](tarea.id, date(2026, 11, 20)) == "Movida: x → 20/11/2026."
    assert h["mover_tarea"](tarea.id, None) == "Sin día: x."
    assert h["borrar_tarea"](tarea.id) == "Tarea borrada."
    with pytest.raises(TareaNoEncontrada):
        h["completar_tarea"](tarea.id)


def test_evento_con_hora_local_y_aviso(h: Herramientas, casos: CasosUsoPlanning):
    casos.crear_bloque("Cálculo", 0, time(9), time(11))
    texto = h["crear_evento"]("Médico", datetime(2026, 11, 16, 10), datetime(2026, 11, 16, 12))

    assert texto == "Evento creado: Médico el 16/11/2026 de 10:00 a 12:00. Se pisa con: Cálculo."
    agenda = h["agenda"](LUNES)
    assert "- 09:00-11:00 Cálculo" in agenda and "- 10:00-12:00 Médico" in agenda
    (evento,) = [c for c in casos.agenda(LUNES).citas if c.titulo == "Médico"]
    assert evento.inicio == a_las(10)
    assert h["borrar_evento"](evento.id) == "Evento borrado."
