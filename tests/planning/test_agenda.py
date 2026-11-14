from __future__ import annotations

from datetime import UTC, date, datetime, time

from modules.planning.domain.agenda import TipoCita, agenda_del_dia, limites_del_dia
from modules.planning.domain.eventos import BloqueRecurrente, Evento, bloques_se_solapan
from modules.planning.domain.tareas import Prioridad, Tarea
from tests.planning.conftest import LUNES, MADRID, ZONA, a_las

CREADA = datetime(2026, 11, 1, tzinfo=UTC)


def tarea(titulo: str, fecha: date | None, prioridad: Prioridad = Prioridad.MEDIA) -> Tarea:
    return Tarea(titulo=titulo, fecha=fecha, prioridad=prioridad, creada_en=CREADA)


def bloque(**kwargs: object) -> BloqueRecurrente:
    datos = {"titulo": "x", "dia_semana": 0, "hora_inicio": time(9), "hora_fin": time(11)}
    return BloqueRecurrente(**{**datos, **kwargs})  # type: ignore[arg-type]


def test_limites_del_dia_en_hora_local():
    inicio, fin = limites_del_dia(LUNES, ZONA)
    assert inicio == datetime(2026, 11, 16, 0, 0, tzinfo=MADRID)
    assert fin == datetime(2026, 11, 17, 0, 0, tzinfo=MADRID)


def test_agenda_junta_eventos_y_bloques_por_hora():
    clase = bloque(titulo="Cálculo")
    examen = Evento(titulo="Examen", inicio=a_las(12), fin=a_las(13))
    agenda = agenda_del_dia(LUNES, ZONA, eventos=[examen], bloques=[clase], tareas=[])

    assert [(c.titulo, c.tipo) for c in agenda.citas] == [
        ("Cálculo", TipoCita.BLOQUE),
        ("Examen", TipoCita.EVENTO),
    ]
    assert agenda.citas[0].id == clase.id and agenda.citas[1].id == examen.id


def test_evento_que_cruza_la_medianoche_sale_en_los_dos_dias():
    fiesta = Evento(titulo="Fiesta", inicio=a_las(23), fin=a_las(2, dia=date(2026, 11, 17)))
    lunes = agenda_del_dia(LUNES, ZONA, [fiesta], [], [])
    martes = agenda_del_dia(date(2026, 11, 17), ZONA, [fiesta], [], [])
    miercoles = agenda_del_dia(date(2026, 11, 18), ZONA, [fiesta], [], [])

    assert len(lunes.citas) == len(martes.citas) == 1
    assert miercoles.citas == []


def test_evento_guardado_en_utc_se_muestra_en_hora_local():
    evento = Evento(
        titulo="x",
        inicio=datetime(2026, 11, 16, 8, 0, tzinfo=UTC),
        fin=datetime(2026, 11, 16, 9, 0, tzinfo=UTC),
    )
    cita = agenda_del_dia(LUNES, ZONA, [evento], [], []).citas[0]
    assert cita.inicio.hour == 9 and cita.inicio.tzinfo == MADRID


def test_tareas_pendientes_primero_y_por_prioridad():
    hecha = tarea("hecha", LUNES, Prioridad.ALTA).completar(CREADA)
    baja = tarea("baja", LUNES, Prioridad.BAJA)
    alta = tarea("alta", LUNES, Prioridad.ALTA)
    otro_dia = tarea("otro día", date(2026, 11, 20))

    agenda = agenda_del_dia(LUNES, ZONA, [], [], tareas=[hecha, baja, alta, otro_dia])

    assert [t.titulo for t in agenda.tareas] == ["alta", "baja", "hecha"]


def test_atrasadas_solo_pendientes_y_anteriores():
    vieja = tarea("vieja", date(2026, 11, 10))
    ayer = tarea("ayer", date(2026, 11, 15))
    hecha = tarea("hecha", date(2026, 11, 10)).completar(CREADA)
    futura = tarea("futura", date(2026, 11, 20))

    agenda = agenda_del_dia(LUNES, ZONA, [], [], [], atrasadas=[ayer, vieja, hecha, futura])

    assert [t.titulo for t in agenda.atrasadas] == ["vieja", "ayer"]


def test_bloques_se_solapan():
    base = bloque()
    assert bloques_se_solapan(base, bloque(hora_inicio=time(10), hora_fin=time(12)))
    assert not bloques_se_solapan(base, bloque(hora_inicio=time(11), hora_fin=time(12)))
    assert not bloques_se_solapan(base, bloque(dia_semana=1))
    assert not bloques_se_solapan(base, base)  # consigo mismo no
    cuatri_1 = bloque(desde=date(2026, 9, 1), hasta=date(2026, 12, 31))
    cuatri_2 = bloque(desde=date(2027, 2, 1), hasta=date(2027, 6, 30))
    assert not bloques_se_solapan(cuatri_1, cuatri_2)
    assert bloques_se_solapan(cuatri_1, base)  # base no tiene límites
