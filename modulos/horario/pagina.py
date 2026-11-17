"""Pantalla de horario: pestanas Semana, Bloques y Excepciones.

Solo presentacion: todo lo que guarda o calcula pasa por servicio.
"""

from datetime import date, time, timedelta

import streamlit as st

from modulos.horario import servicio
from nucleo import avisos
from nucleo.fechas import DIAS_CORTOS, DIAS_SEMANA, a_fecha, dia_bonito

TIPO_TEXTO = {"clase": "Clase", "trabajo": "Trabajo", "otro": "Otro"}


def dibujar(jarvis, modulo):
    st.title(modulo.titulo)
    st.caption("Aquí gestionas tus bloques de clase y trabajo; la semana se ve en Agenda.")
    bloques, excepciones = st.tabs(["Bloques", "Excepciones"])
    with bloques:
        pestana_bloques(jarvis)
    with excepciones:
        pestana_excepciones(jarvis)


def _guardado(texto, solapes=None):
    if solapes:
        avisos.avisar("aviso", texto + ", pero se solapa con: " + "; ".join(solapes))
    else:
        avisos.avisar("exito", texto)
    st.rerun()


def _hora(texto):
    partes = texto.split(":")
    return time(int(partes[0]), int(partes[1]))


def _fecha_o_none(texto):
    if texto is None:
        return None
    return a_fecha(texto)


# ======================================================================
# Bloques
# ======================================================================
def formulario_nuevo_bloque(jarvis):
    with st.form("nuevo_bloque", clear_on_submit=True):
        col1, col2 = st.columns([0.3, 0.7])
        tipo = col1.selectbox("Tipo", list(servicio.TIPOS), format_func=TIPO_TEXTO.get)
        titulo = col2.text_input("Título", placeholder="Cálculo, turno de tarde…")
        dias = st.multiselect(
            "Días", list(range(7)), format_func=lambda d: DIAS_SEMANA[d],
            help="Si eliges varios, se crea un bloque por día.",
        )
        col1, col2 = st.columns(2)
        hora_inicio = col1.time_input("Empieza", value=time(9, 0))
        hora_fin = col2.time_input("Acaba", value=time(11, 0))
        ubicacion = st.text_input("Ubicación")
        col1, col2 = st.columns(2)
        desde = col1.date_input("Vigente desde", value=date.today(), format="DD/MM/YYYY")
        hasta = col2.date_input(
            "Vigente hasta", value=None, format="DD/MM/YYYY", help="Vacío = sin fecha de fin.",
        )
        crear = st.form_submit_button("Añadir", type="primary")
    if crear:
        try:
            solapes = servicio.crear_bloques(jarvis, tipo, titulo, dias, hora_inicio, hora_fin, ubicacion, desde, hasta)
            texto = "Bloque añadido"
            if len(dias) > 1:
                texto = str(len(dias)) + " bloques añadidos"
            _guardado(texto, solapes)
        except ValueError as error:
            st.error(str(error))


def formulario_editar_bloque(jarvis, bloque):
    bloque_id = bloque["id"]
    with st.form("editar_bloque_" + str(bloque_id)):
        col1, col2 = st.columns([0.4, 0.6])
        tipo = col1.selectbox(
            "Tipo", list(servicio.TIPOS), index=servicio.TIPOS.index(bloque["tipo"]), format_func=TIPO_TEXTO.get,
        )
        titulo = col2.text_input("Título", value=bloque["titulo"])
        dia_semana = st.selectbox(
            "Día", list(range(7)), index=bloque["dia_semana"], format_func=lambda d: DIAS_SEMANA[d],
        )
        col1, col2 = st.columns(2)
        hora_inicio = col1.time_input("Empieza", value=_hora(bloque["hora_inicio"]))
        hora_fin = col2.time_input("Acaba", value=_hora(bloque["hora_fin"]))
        ubicacion = st.text_input("Ubicación", value=bloque["ubicacion"] or "")
        col1, col2 = st.columns(2)
        desde = col1.date_input("Vigente desde", value=a_fecha(bloque["vigente_desde"]), format="DD/MM/YYYY")
        hasta = col2.date_input("Vigente hasta", value=_fecha_o_none(bloque["vigente_hasta"]), format="DD/MM/YYYY")
        guardar = st.form_submit_button("Guardar", type="primary")
    if guardar:
        try:
            solapes = servicio.editar_bloque(
                jarvis, bloque_id, tipo, titulo, dia_semana, hora_inicio, hora_fin, ubicacion, desde, hasta,
            )
            _guardado("Bloque actualizado", solapes)
        except ValueError as error:
            st.error(str(error))
    if st.button("Borrar bloque", key="borrar_bloque_" + str(bloque_id), help="Borra también sus excepciones."):
        servicio.borrar_bloque(jarvis, bloque_id)
        _guardado("Bloque borrado")


def _vigencia(bloque):
    hoy = date.today().isoformat()
    if bloque["vigente_hasta"] is not None and bloque["vigente_hasta"] < hoy:
        return "terminó el " + dia_bonito(bloque["vigente_hasta"])
    if bloque["vigente_desde"] > hoy:
        return "empieza el " + dia_bonito(bloque["vigente_desde"])
    if bloque["vigente_hasta"] is not None:
        return "hasta el " + dia_bonito(bloque["vigente_hasta"])
    return None


def pestana_bloques(jarvis):
    with st.expander("Nuevo bloque"):
        formulario_nuevo_bloque(jarvis)

    lista = servicio.bloques(jarvis)
    if len(lista) == 0:
        st.info("Todavía no hay horario. Añade tu primer bloque de clase o trabajo.")
        return

    dia_actual = None
    for bloque in lista:
        if bloque["dia_semana"] != dia_actual:
            dia_actual = bloque["dia_semana"]
            st.markdown("##### " + DIAS_SEMANA[dia_actual])
        col_texto, col_menu = st.columns([0.85, 0.15], vertical_alignment="center")
        col_texto.markdown(
            "**" + bloque["hora_inicio"] + "–" + bloque["hora_fin"] + "** · "
            + bloque["titulo"] + " (" + TIPO_TEXTO[bloque["tipo"]].lower() + ")"
        )
        trozos = []
        if bloque["ubicacion"]:
            trozos.append(bloque["ubicacion"])
        vigencia = _vigencia(bloque)
        if vigencia is not None:
            trozos.append(vigencia)
        if trozos:
            col_texto.caption(" · ".join(trozos))
        with col_menu.popover("Editar"):
            formulario_editar_bloque(jarvis, bloque)


# ======================================================================
# Excepciones
# ======================================================================
def _nombre_bloque(bloque):
    return DIAS_CORTOS[bloque["dia_semana"]] + " " + bloque["hora_inicio"] + " · " + bloque["titulo"]


def pestana_excepciones(jarvis):
    st.caption("Un día concreto en el que un bloque se cancela o cambia de hora (festivos, cambios de turno…).")
    lista = servicio.bloques(jarvis)
    if len(lista) == 0:
        st.info("Primero añade algún bloque en la pestaña Bloques.")
        return

    por_id = {}
    for bloque in lista:
        por_id[bloque["id"]] = bloque

    with st.form("nueva_excepcion", clear_on_submit=True):
        bloque_id = st.selectbox("Bloque", list(por_id), format_func=lambda i: _nombre_bloque(por_id[i]))
        fecha = st.date_input("Día", value=a_fecha(jarvis.fecha_activa), format="DD/MM/YYYY")
        que = st.radio("¿Qué pasa ese día?", ["Se cancela", "Cambia de hora"], horizontal=True)
        col1, col2 = st.columns(2)
        hora_inicio = col1.time_input("Nueva hora de inicio", value=time(9, 0), help="Solo si cambia de hora.")
        hora_fin = col2.time_input("Nueva hora de fin", value=time(11, 0), help="Solo si cambia de hora.")
        motivo = st.text_input("Motivo", placeholder="Festivo, examen, cambio de turno…")
        guardar = st.form_submit_button("Guardar excepción", type="primary")
    if guardar:
        try:
            servicio.guardar_excepcion(
                jarvis, bloque_id, fecha, que == "Se cancela", hora_inicio, hora_fin, motivo,
            )
            _guardado("Excepción guardada")
        except ValueError as error:
            st.error(str(error))

    st.markdown("##### Próximas excepciones")
    proximas = servicio.proximas_excepciones(jarvis, date.today() - timedelta(days=7))
    if len(proximas) == 0:
        st.caption("Ninguna.")
    for excepcion in proximas:
        col_texto, col_boton = st.columns([0.90, 0.10], vertical_alignment="center")
        if excepcion["tipo"] == "cancelado":
            que = "cancelado"
        else:
            que = excepcion["hora_inicio"] + "–" + excepcion["hora_fin"] + " (normalmente " + excepcion["hora_inicio_normal"] + "–" + excepcion["hora_fin_normal"] + ")"
        col_texto.markdown("**" + dia_bonito(excepcion["fecha"]) + "** · " + excepcion["titulo"] + " · " + que)
        if excepcion["motivo"]:
            col_texto.caption(excepcion["motivo"])
        if col_boton.button("Quitar", key="borrar_excepcion_" + str(excepcion["id"]), help="Quitar excepción"):
            servicio.borrar_excepcion(jarvis, excepcion["id"])
            _guardado("Excepción quitada")
