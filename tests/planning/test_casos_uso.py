from __future__ import annotations

from datetime import date, time

import pytest

from modules.planning.application.casos_uso import CasosUsoPlanning
from modules.planning.domain.errores import (
    BloqueNoEncontrado,
    CalendarioInvalido,
    EventoNoEncontrado,
    TareaInvalida,
    TareaNoEncontrada,
)
from modules.planning.domain.tareas import EstadoTarea, Prioridad
from tests.planning.conftest import AHORA, LUNES, a_las

MARTES = date(2026, 11, 17)


# --- Tareas -----------------------------------------------------------------------------------


def test_crear_tarea_y_verla_en_la_agenda(casos: CasosUsoPlanning):
    tarea = casos.crear_tarea("estudiar cálculo", fecha=LUNES, prioridad=Prioridad.ALTA)

    assert tarea.estado is EstadoTarea.PENDIENTE and tarea.creada_en == AHORA
    assert casos.agenda(LUNES).tareas == [tarea]


def test_prioridad_se_acepta_como_texto(casos: CasosUsoPlanning):
    """El agente y la API mandan texto: "alta" debe valer igual que Prioridad.ALTA."""
    assert casos.crear_tarea("x", prioridad="alta").prioridad is Prioridad.ALTA  # type: ignore[arg-type]


def test_tarea_sin_fecha_va_a_la_bandeja(casos: CasosUsoPlanning):
    tarea = casos.crear_tarea("comprar pilas")
    assert casos.tareas_sin_fecha() == [tarea]
    assert casos.agenda(LUNES).tareas == []


def test_titulo_vacio_no_se_guarda(casos: CasosUsoPlanning):
    with pytest.raises(TareaInvalida):
        casos.crear_tarea("   ")
    assert casos.tareas_sin_fecha() == []


def test_completar_y_reabrir(casos: CasosUsoPlanning):
    tarea = casos.crear_tarea("x", fecha=LUNES)

    hecha = casos.completar_tarea(tarea.id)
    assert hecha.hecha and hecha.hecha_en == AHORA
    assert casos.agenda(LUNES).tareas[0].hecha

    assert not casos.reabrir_tarea(tarea.id).hecha
    assert not casos.agenda(LUNES).tareas[0].hecha


def test_mover_tarea_cambia_de_dia(casos: CasosUsoPlanning):
    tarea = casos.crear_tarea("x", fecha=LUNES)
    casos.mover_tarea(tarea.id, MARTES)

    assert casos.agenda(LUNES).tareas == []
    assert [t.id for t in casos.agenda(MARTES).tareas] == [tarea.id]


def test_pendiente_de_otro_dia_sale_como_atrasada(casos: CasosUsoPlanning):
    vieja = casos.crear_tarea("vieja", fecha=LUNES)
    hecha = casos.crear_tarea("hecha", fecha=LUNES)
    casos.completar_tarea(hecha.id)

    assert [t.id for t in casos.agenda(MARTES).atrasadas] == [vieja.id]


def test_borrar_tarea(casos: CasosUsoPlanning):
    tarea = casos.crear_tarea("x", fecha=LUNES)
    otra = casos.crear_tarea("y", fecha=LUNES)
    casos.borrar_tarea(tarea.id)

    assert [t.id for t in casos.agenda(LUNES).tareas] == [otra.id]
    with pytest.raises(TareaNoEncontrada):
        casos.borrar_tarea(tarea.id)


@pytest.mark.parametrize("operacion", ["completar_tarea", "reabrir_tarea"])
def test_tarea_que_no_existe(casos: CasosUsoPlanning, operacion: str):
    with pytest.raises(TareaNoEncontrada):
        getattr(casos, operacion)("no-existe")


# --- Eventos y solapes ------------------------------------------------------------------------


def test_crear_evento_sin_solapes(casos: CasosUsoPlanning):
    guardado = casos.crear_evento("Examen", a_las(12), a_las(13), lugar="Aula 2")

    assert guardado.avisos == []
    cita = casos.agenda(LUNES).citas[0]
    assert (cita.titulo, cita.inicio, cita.lugar) == ("Examen", a_las(12), "Aula 2")


def test_solape_avisa_pero_guarda(casos: CasosUsoPlanning):
    casos.crear_bloque("Cálculo", dia_semana=0, hora_inicio=time(9), hora_fin=time(11))
    casos.crear_evento("Tutoría", a_las(10, 30), a_las(11, 30))

    guardado = casos.crear_evento("Médico", a_las(10), a_las(12))

    assert [a.titulo for a in guardado.avisos] == ["Cálculo", "Tutoría"]
    assert len(casos.agenda(LUNES).citas) == 3  # se guardó igualmente


def test_mover_evento_no_avisa_de_si_mismo(casos: CasosUsoPlanning):
    evento = casos.crear_evento("Examen", a_las(12), a_las(13)).evento

    movido = casos.mover_evento(evento.id, a_las(12, 30), a_las(13, 30))

    assert movido.avisos == []
    assert casos.agenda(LUNES).citas[0].inicio == a_las(12, 30)


def test_borrar_evento(casos: CasosUsoPlanning):
    evento = casos.crear_evento("x", a_las(12), a_las(13)).evento
    casos.borrar_evento(evento.id)

    assert casos.agenda(LUNES).citas == []
    with pytest.raises(EventoNoEncontrado):
        casos.borrar_evento(evento.id)
    with pytest.raises(EventoNoEncontrado):
        casos.mover_evento(evento.id, a_las(12), a_las(13))


# --- Bloques ----------------------------------------------------------------------------------


def test_bloque_aparece_todos_los_lunes(casos: CasosUsoPlanning):
    casos.crear_bloque("Cálculo", dia_semana=0, hora_inicio=time(9), hora_fin=time(11), lugar="A1")

    for lunes in (LUNES, date(2026, 11, 23), date(2026, 11, 30)):
        citas = casos.agenda(lunes).citas
        assert [(c.titulo, c.inicio.hour, c.lugar) for c in citas] == [("Cálculo", 9, "A1")]
    assert casos.agenda(MARTES).citas == []


def test_bloque_solapado_avisa(casos: CasosUsoPlanning):
    calculo = casos.crear_bloque("Cálculo", 0, time(9), time(11)).bloque
    guardado = casos.crear_bloque("Física", 0, time(10), time(12))

    assert [b.id for b in guardado.avisos] == [calculo.id]
    assert len(casos.listar_bloques()) == 2


def test_borrar_bloque(casos: CasosUsoPlanning):
    bloque = casos.crear_bloque("Cálculo", 0, time(9), time(11)).bloque
    casos.borrar_bloque(bloque.id)

    assert casos.agenda(LUNES).citas == []
    with pytest.raises(BloqueNoEncontrado):
        casos.borrar_bloque(bloque.id)


# --- Importar un .ics -------------------------------------------------------------------------


def calendario(titulo: str = "Cálculo", hora: str = "090000") -> bytes:
    """Clase semanal los lunes desde el 16/11/2026, 3 semanas."""
    return (
        "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//test//ES\r\nBEGIN:VEVENT\r\n"
        f"UID:calc\r\nSUMMARY:{titulo}\r\nDTSTART;TZID=Europe/Madrid:20261116T{hora}\r\n"
        "DURATION:PT2H\r\nRRULE:FREQ=WEEKLY;COUNT=3\r\nLOCATION:A1\r\n"
        "END:VEVENT\r\nEND:VCALENDAR\r\n"
    ).encode()


def test_importar_añade_las_clases_a_la_agenda(casos: CasosUsoPlanning):
    resultado = casos.importar_calendario(calendario())

    assert (resultado.nuevos, resultado.actualizados, resultado.sin_cambios) == (3, 0, 0)
    citas = casos.agenda(date(2026, 11, 23)).citas
    assert [(c.titulo, c.inicio.hour, c.lugar) for c in citas] == [("Cálculo", 9, "A1")]


def test_reimportar_no_duplica_y_actualiza_lo_cambiado(casos: CasosUsoPlanning):
    casos.importar_calendario(calendario())

    igual = casos.importar_calendario(calendario())
    assert (igual.nuevos, igual.actualizados, igual.sin_cambios) == (0, 0, 3)

    cambiado = casos.importar_calendario(calendario("Cálculo I"))
    assert (cambiado.nuevos, cambiado.actualizados) == (0, 3)
    assert [c.titulo for c in casos.agenda(LUNES).citas] == ["Cálculo I"]


def test_importar_avisa_de_lo_omitido(casos: CasosUsoPlanning):
    festivo = (
        b"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:x\r\nBEGIN:VEVENT\r\nUID:f\r\n"
        b"SUMMARY:Festivo\r\nDTSTART;VALUE=DATE:20261208\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n"
    )
    resultado = casos.importar_calendario(festivo)

    assert resultado.nuevos == 0
    assert resultado.omitidos == ["«Festivo»: es de día completo"]


def test_importar_un_fichero_que_no_es_ics(casos: CasosUsoPlanning):
    with pytest.raises(CalendarioInvalido):
        casos.importar_calendario(b"hola")
