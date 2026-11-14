from __future__ import annotations

from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

import pytest

from modules.planning.domain.errores import BloqueInvalido, EventoInvalido, TareaInvalida
from modules.planning.domain.eventos import (
    BloqueRecurrente,
    Evento,
    OrigenEvento,
    se_solapan,
    solapes,
)
from modules.planning.domain.tareas import EstadoTarea, Prioridad, Tarea

MADRID = ZoneInfo("Europe/Madrid")
AHORA = datetime(2026, 11, 14, 10, 0, tzinfo=UTC)


def a_las(hora: int, minuto: int = 0, dia: date = date(2026, 11, 16)) -> datetime:
    return datetime.combine(dia, time(hora, minuto), tzinfo=MADRID)


def evento(titulo: str, inicio: datetime, fin: datetime) -> Evento:
    return Evento(titulo=titulo, inicio=inicio, fin=fin)


# --- Tareas ---------------------------------------------------------------------------------


def test_tarea_por_defecto_es_pendiente_y_de_prioridad_media():
    tarea = Tarea(titulo="  estudiar   cálculo ", creada_en=AHORA)
    assert tarea.titulo == "estudiar cálculo"
    assert tarea.estado is EstadoTarea.PENDIENTE
    assert tarea.prioridad is Prioridad.MEDIA
    assert tarea.fecha is None and tarea.hecha_en is None


@pytest.mark.parametrize(
    "kwargs",
    [
        {"titulo": "   "},
        {"creada_en": datetime(2026, 11, 14, 10, 0)},  # sin zona
        {"estimacion_min": 0},
        {"estimacion_min": True},
        {"estado": EstadoTarea.HECHA},  # hecha sin hecha_en
        {"hecha_en": AHORA},  # pendiente con hecha_en
    ],
)
def test_tarea_invalida(kwargs):
    datos = {"titulo": "algo", "creada_en": AHORA, **kwargs}
    with pytest.raises(TareaInvalida):
        Tarea(**datos)


def test_completar_reabrir_y_mover_devuelven_tareas_nuevas():
    tarea = Tarea(titulo="algo", creada_en=AHORA)
    hecha = tarea.completar(AHORA)
    assert hecha.hecha and hecha.hecha_en == AHORA and hecha.id == tarea.id
    assert not tarea.hecha  # la original no cambia
    assert hecha.completar(datetime(2026, 12, 1, tzinfo=UTC)) is hecha  # ya estaba hecha
    assert not hecha.reabrir().hecha and hecha.reabrir().hecha_en is None
    assert tarea.mover(date(2026, 11, 15)).fecha == date(2026, 11, 15)


def test_valores_guardados_de_los_enum_no_cambian():
    assert [p.value for p in Prioridad] == ["baja", "media", "alta"]
    assert [e.value for e in EstadoTarea] == ["pendiente", "hecha"]
    assert [o.value for o in OrigenEvento] == ["manual", "ics"]


# --- Eventos --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"titulo": ""},
        {"fin": a_las(9)},  # fin == inicio
        {"fin": a_las(8)},  # fin < inicio
        {"inicio": datetime(2026, 11, 16, 9, 0)},  # sin zona
        {"origen": OrigenEvento.ICS},  # .ics sin uid
    ],
)
def test_evento_invalido(kwargs):
    datos = {"titulo": "clase", "inicio": a_las(9), "fin": a_las(10), **kwargs}
    with pytest.raises(EventoInvalido):
        Evento(**datos)


def test_evento_ics_con_uid_es_valido():
    e = Evento(
        titulo="Cálculo", inicio=a_las(9), fin=a_las(11), origen=OrigenEvento.ICS, uid_externo="x"
    )
    assert e.origen is OrigenEvento.ICS


# --- Bloques recurrentes --------------------------------------------------------------------


def test_bloque_se_expande_cada_semana_en_hora_local():
    lunes = BloqueRecurrente(titulo="Cálculo", dia_semana=0, hora_inicio=time(9), hora_fin=time(11))
    ocurrencias = lunes.ocurrencias(date(2026, 11, 14), date(2026, 11, 30), "Europe/Madrid")
    assert [o.inicio.date() for o in ocurrencias] == [
        date(2026, 11, 16),
        date(2026, 11, 23),
        date(2026, 11, 30),
    ]
    assert ocurrencias[0].inicio == a_las(9) and ocurrencias[0].fin == a_las(11)
    assert ocurrencias[0].bloque_id == lunes.id


def test_bloque_respeta_su_periodo():
    bloque = BloqueRecurrente(
        titulo="Cálculo",
        dia_semana=0,
        hora_inicio=time(9),
        hora_fin=time(11),
        desde=date(2026, 11, 20),
        hasta=date(2026, 11, 25),
    )
    ocurrencias = bloque.ocurrencias(date(2026, 11, 1), date(2026, 12, 31), "Europe/Madrid")
    assert [o.inicio.date() for o in ocurrencias] == [date(2026, 11, 23)]


def test_bloque_fuera_de_rango_no_da_ocurrencias():
    bloque = BloqueRecurrente(titulo="x", dia_semana=2, hora_inicio=time(9), hora_fin=time(10))
    assert bloque.ocurrencias(date(2026, 11, 16), date(2026, 11, 17), "Europe/Madrid") == []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"titulo": " "},
        {"dia_semana": 7},
        {"dia_semana": -1},
        {"hora_fin": time(9)},
        {"desde": date(2026, 12, 1), "hasta": date(2026, 11, 1)},
    ],
)
def test_bloque_invalido(kwargs):
    datos = {"titulo": "x", "dia_semana": 0, "hora_inicio": time(9), "hora_fin": time(10)}
    with pytest.raises(BloqueInvalido):
        BloqueRecurrente(**{**datos, **kwargs})


# --- Solapes --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("otro_inicio", "otro_fin", "esperado"),
    [
        (a_las(10), a_las(12), True),  # empieza dentro
        (a_las(8), a_las(9, 30), True),  # termina dentro
        (a_las(8), a_las(12), True),  # lo contiene
        (a_las(11), a_las(12), False),  # se tocan: 9-11 y 11-12
        (a_las(7), a_las(9), False),  # se tocan por el otro lado
    ],
)
def test_se_solapan(otro_inicio, otro_fin, esperado):
    base = evento("base", a_las(9), a_las(11))
    assert se_solapan(base, evento("otro", otro_inicio, otro_fin)) is esperado


def test_solapes_avisa_ordenado_y_no_consigo_mismo():
    nuevo = evento("examen", a_las(9), a_las(12))
    clase = BloqueRecurrente(
        titulo="Cálculo", dia_semana=0, hora_inicio=time(11), hora_fin=time(13)
    )
    existentes = [
        *clase.ocurrencias(date(2026, 11, 16), date(2026, 11, 16), "Europe/Madrid"),
        evento("tutoría", a_las(9, 30), a_las(10)),
        evento("comida", a_las(14), a_las(15)),
        nuevo,  # al editar, el propio evento ya está guardado
    ]
    avisos = solapes(nuevo, existentes)
    assert [a.titulo for a in avisos] == ["tutoría", "Cálculo"]
