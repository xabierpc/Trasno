from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from modules.planning.domain.errores import CalendarioInvalido
from modules.planning.domain.eventos import LecturaCalendario, OrigenEvento
from modules.planning.infrastructure.ics import LectorIcs
from tests.planning.conftest import MADRID, ZONA

DESDE, HASTA = date(2026, 9, 1), date(2027, 6, 30)
INICIO = "DTSTART;TZID=Europe/Madrid:20261116T090000"
FIN = "DTEND;TZID=Europe/Madrid:20261116T110000"


def ics(*eventos: str) -> bytes:
    """Un VCALENDAR con los VEVENT dados, con saltos de línea CRLF como manda el estándar."""
    texto = "\n".join(["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//test//ES", *eventos])
    return (texto + "\nEND:VCALENDAR\n").replace("\n", "\r\n").encode()


def vevent(
    uid: str | None = "e1",
    resumen: str = "Cálculo",
    inicio: str = INICIO,
    fin: str = FIN,
    *extra: str,
) -> str:
    lineas = ["BEGIN:VEVENT", f"SUMMARY:{resumen}", inicio, fin, *extra, "END:VEVENT"]
    if uid is not None:
        lineas.insert(1, f"UID:{uid}")
    return "\n".join(lineas)


def leer(contenido: bytes, desde: date = DESDE, hasta: date = HASTA) -> LecturaCalendario:
    return LectorIcs(ZONA).leer(contenido, desde, hasta)


def test_evento_simple_con_zona_y_lugar():
    (evento,) = leer(ics(vevent("e1", "Cálculo", INICIO, FIN, "LOCATION:Aula 1.2"))).eventos

    assert evento.titulo == "Cálculo" and evento.lugar == "Aula 1.2"
    assert evento.inicio == datetime(2026, 11, 16, 9, 0, tzinfo=MADRID)
    assert evento.fin == datetime(2026, 11, 16, 11, 0, tzinfo=MADRID)
    assert (evento.origen, evento.uid_externo) == (OrigenEvento.ICS, "e1")


def test_hora_en_utc_y_hora_flotante():
    utc = vevent("u", "UTC", "DTSTART:20261116T080000Z", "DTEND:20261116T090000Z")
    flotante = vevent("f", "Flotante", "DTSTART:20261116T120000", "DTEND:20261116T130000")
    eventos = {e.titulo: e for e in leer(ics(utc, flotante)).eventos}

    assert eventos["UTC"].inicio.astimezone(MADRID).hour == 9
    assert eventos["Flotante"].inicio == datetime(2026, 11, 16, 12, 0, tzinfo=MADRID)


def test_duracion_en_lugar_de_dtend():
    (evento,) = leer(ics(vevent("d", "x", "DTSTART:20261116T120000", "DURATION:PT90M"))).eventos
    assert evento.fin - evento.inicio == timedelta(minutes=90)


def test_clase_semanal_conserva_la_hora_local_al_cambiar_al_horario_de_invierno():
    # El 25/10/2026 se atrasa la hora: los lunes 19/10 y 26/10 tienen distinto desfase con UTC
    clase = vevent(
        "calc",
        "Cálculo",
        "DTSTART;TZID=Europe/Madrid:20261019T090000",
        "DTEND;TZID=Europe/Madrid:20261019T110000",
        "RRULE:FREQ=WEEKLY;UNTIL=20261102T235959Z",
    )
    eventos = leer(ics(clase)).eventos

    assert [e.inicio.date() for e in eventos] == [
        date(2026, 10, 19),
        date(2026, 10, 26),
        date(2026, 11, 2),
    ]
    assert {e.inicio.astimezone(MADRID).hour for e in eventos} == {9}
    assert [e.uid_externo for e in eventos] == [
        "calc@20261019T070000Z",
        "calc@20261026T080000Z",
        "calc@20261102T080000Z",
    ]


def test_exdate_y_ocurrencias_movida_y_anulada():
    base = vevent(
        "calc",
        "Cálculo",
        "DTSTART;TZID=Europe/Madrid:20261102T090000",
        "DTEND;TZID=Europe/Madrid:20261102T110000",
        "RRULE:FREQ=WEEKLY;COUNT=4",
        "EXDATE;TZID=Europe/Madrid:20261109T090000",
    )
    movida = vevent(
        "calc",
        "Cálculo (aula cambiada)",
        "DTSTART;TZID=Europe/Madrid:20261116T120000",
        "DTEND;TZID=Europe/Madrid:20261116T140000",
        "RECURRENCE-ID;TZID=Europe/Madrid:20261116T090000",
    )
    anulada = vevent(
        "calc",
        "Cálculo",
        "DTSTART;TZID=Europe/Madrid:20261123T090000",
        "DTEND;TZID=Europe/Madrid:20261123T110000",
        "RECURRENCE-ID;TZID=Europe/Madrid:20261123T090000",
        "STATUS:CANCELLED",
    )
    eventos = leer(ics(anulada, movida, base)).eventos  # el orden en el fichero no importa

    assert [(e.inicio.date(), e.inicio.hour, e.titulo) for e in eventos] == [
        (date(2026, 11, 2), 9, "Cálculo"),
        (date(2026, 11, 16), 12, "Cálculo (aula cambiada)"),
    ]


def test_solo_lee_lo_que_empieza_dentro_de_la_ventana():
    sin_fin = vevent(
        "i",
        "Semanal",
        "DTSTART;TZID=Europe/Madrid:20260105T090000",
        "DTEND;TZID=Europe/Madrid:20260105T100000",
        "RRULE:FREQ=WEEKLY",
    )
    fuera = vevent("fuera", "Fuera", "DTSTART:20261201T090000", "DTEND:20261201T100000")

    eventos = leer(ics(sin_fin, fuera), date(2026, 11, 14), date(2026, 11, 30)).eventos

    assert [(e.titulo, e.inicio.date()) for e in eventos] == [
        ("Semanal", date(2026, 11, 16)),
        ("Semanal", date(2026, 11, 23)),
        ("Semanal", date(2026, 11, 30)),
    ]


def test_omite_dia_completo_cancelados_sin_uid_e_incoherentes():
    festivo = vevent("f", "Festivo", "DTSTART;VALUE=DATE:20261208", "DTEND;VALUE=DATE:20261209")
    cancelado = vevent("c", "Anulado", INICIO, FIN, "STATUS:CANCELLED")
    sin_uid = vevent(None, "Huérfano")
    al_reves = vevent("r", "Al revés", fin="DTEND;TZID=Europe/Madrid:20261116T080000")

    lectura = leer(ics(festivo, cancelado, sin_uid, al_reves, vevent()))

    assert [e.titulo for e in lectura.eventos] == ["Cálculo"]
    omitidos = " | ".join(lectura.omitidos)
    for texto in ("«Festivo»: es de día completo", "«Anulado»: está cancelado"):
        assert texto in omitidos
    assert "«Huérfano»: no tiene UID" in omitidos and "«Al revés»" in omitidos


@pytest.mark.parametrize(
    "contenido", [b"esto no es un calendario", b"BEGIN:VEVENT\r\nEND:VEVENT\r\n"]
)
def test_fichero_no_valido(contenido: bytes):
    with pytest.raises(CalendarioInvalido):
        leer(contenido)
