from __future__ import annotations

from datetime import date, datetime

import pytest

from agent.agente import MAX_PASOS, AccionNoPendiente
from agent.mensajes import Mensaje, Rol
from agent.prompt import es_madrugada, instrucciones
from core.acciones import RegistroAccionesSQL
from core.contracts import EstadoAccion, Tool
from tests.agente.conftest import (
    VENTANA,
    Agenda,
    LLMGuion,
    crear_agente,
    dice,
    llamada,
    pide,
)

USUARIO = [Mensaje(rol=Rol.USUARIO, contenido="hola")]


def test_respuesta_sin_herramientas(herramientas: list[Tool], acciones: RegistroAccionesSQL):
    llm = LLMGuion(dice("¡Hola!"))
    respuesta = crear_agente(llm, herramientas, acciones).conversar(USUARIO)

    assert respuesta.texto == "¡Hola!"
    assert respuesta.ejecutadas == respuesta.propuestas == []
    sistema, usuario = llm.recibidos[0]
    assert (
        sistema.rol is Rol.SISTEMA
        and "lunes 16/11/2026 (2026-11-16), las 10:00" in sistema.contenido
    )
    assert usuario.contenido == "hola"
    assert {h["function"]["name"] for h in llm.herramientas[0]} == {
        "crear_tarea",
        "registrar_peso",
        "rompe",
    }


def test_ejecuta_la_herramienta_y_le_devuelve_el_resultado(
    herramientas: list[Tool], acciones: RegistroAccionesSQL
):
    llm = LLMGuion(pide(llamada("registrar_peso", kg=74.3, fecha="2026-11-16")), dice("Apuntado."))

    respuesta = crear_agente(llm, herramientas, acciones).conversar(USUARIO)

    assert respuesta.texto == "Apuntado."
    (accion,) = respuesta.ejecutadas
    assert (accion.herramienta, accion.estado) == ("registrar_peso", EstadoAccion.EJECUTADA)
    assert accion.resultado == "Peso 74.3 el 2026-11-16"  # la fecha llegó como date
    assert accion.argumentos == {"kg": 74.3, "fecha": "2026-11-16"}
    respuesta_herramienta = llm.recibidos[1][-1]
    assert (respuesta_herramienta.rol, respuesta_herramienta.llamada_id) == (Rol.HERRAMIENTA, "c1")
    assert respuesta_herramienta.contenido == "Peso 74.3 el 2026-11-16"
    assert acciones.recientes() == [accion]


def test_con_confirmacion_solo_propone(
    herramientas: list[Tool], acciones: RegistroAccionesSQL, agenda: Agenda
):
    llm = LLMGuion(
        pide(llamada("crear_tarea", titulo="estudiar cálculo", fecha="2026-11-17")),
        dice("Te creo la tarea, confírmalo."),
    )
    agente = crear_agente(llm, herramientas, acciones)

    respuesta = agente.conversar(USUARIO)

    (propuesta,) = respuesta.propuestas
    assert propuesta.estado is EstadoAccion.PROPUESTA and agenda.tareas == []
    assert "Pendiente de confirmación" in llm.recibidos[1][-1].contenido

    hecha = agente.confirmar(propuesta.id, aceptar=True)  # type: ignore[arg-type]
    assert (hecha.estado, hecha.resultado) == (
        EstadoAccion.EJECUTADA,
        "Tarea creada: estudiar cálculo",
    )
    assert agenda.tareas == [("estudiar cálculo", date(2026, 11, 17))]
    with pytest.raises(AccionNoPendiente):
        agente.confirmar(propuesta.id, aceptar=True)  # type: ignore[arg-type]


def test_cancelar_una_propuesta(
    herramientas: list[Tool], acciones: RegistroAccionesSQL, agenda: Agenda
):
    llm = LLMGuion(pide(llamada("crear_tarea", titulo="x")), dice("¿Confirmas?"))
    agente = crear_agente(llm, herramientas, acciones)
    (propuesta,) = agente.conversar(USUARIO).propuestas

    cancelada = agente.confirmar(propuesta.id, aceptar=False)  # type: ignore[arg-type]

    assert cancelada.estado is EstadoAccion.CANCELADA and agenda.tareas == []


def test_confirmar_algo_que_no_existe(herramientas: list[Tool], acciones: RegistroAccionesSQL):
    with pytest.raises(AccionNoPendiente):
        crear_agente(LLMGuion(), herramientas, acciones).confirmar(99, aceptar=True)


def test_argumentos_no_validos_vuelven_al_llm_para_que_corrija(
    herramientas: list[Tool], acciones: RegistroAccionesSQL
):
    llm = LLMGuion(
        pide(llamada("registrar_peso", kg="mucho", fecha="2026-11-16")),
        pide(llamada("registrar_peso", id_llamada="c2", kg=74.3, fecha="2026-11-16")),
        dice("Listo."),
    )

    respuesta = crear_agente(llm, herramientas, acciones).conversar(USUARIO)

    error = llm.recibidos[1][-1].contenido
    assert error.startswith("Error en los argumentos: kg:")
    assert [a.estado for a in respuesta.ejecutadas] == [EstadoAccion.EJECUTADA]
    assert len(acciones.recientes()) == 1  # el intento erróneo no se ejecutó ni se registró


def test_herramienta_desconocida_y_que_falla(
    herramientas: list[Tool], acciones: RegistroAccionesSQL
):
    llm = LLMGuion(pide(llamada("vuela"), llamada("rompe", id_llamada="c2")), dice("Vaya."))

    respuesta = crear_agente(llm, herramientas, acciones).conversar(USUARIO)

    desconocida, fallida = llm.recibidos[1][-2:]
    assert desconocida.contenido == "Error: no existe la herramienta 'vuela'."
    assert fallida.contenido == "Error: boom"
    assert [a.estado for a in respuesta.ejecutadas] == [EstadoAccion.FALLIDA]


def test_limite_de_pasos(herramientas: list[Tool], acciones: RegistroAccionesSQL):
    llm = LLMGuion(*[pide(llamada("rompe", id_llamada=str(n))) for n in range(MAX_PASOS)])

    respuesta = crear_agente(llm, herramientas, acciones).conversar(USUARIO)

    assert respuesta.texto.startswith("No he conseguido terminar")
    assert len(llm.recibidos) == MAX_PASOS


def test_de_madrugada_pide_preguntar_ayer_u_hoy():
    madrugada = datetime(2026, 11, 16, 1, 30)
    assert es_madrugada(madrugada, VENTANA)
    assert not es_madrugada(madrugada.replace(hour=7), VENTANA)
    assert es_madrugada(
        madrugada.replace(hour=23), (datetime.min.time().replace(hour=22), VENTANA[1])
    )
    assert "ayer o para hoy" in instrucciones(madrugada, VENTANA)
    assert "ayer o para hoy" not in instrucciones(madrugada.replace(hour=10), VENTANA)
