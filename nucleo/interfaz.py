"""Interfaz Streamlit del nucleo: menu, portada, ajustes y pregunta de madrugada.

Cada modulo dibuja su propia pagina; aqui solo se monta el marco.
"""

from datetime import datetime

import streamlit as st

from nucleo.fechas import es_madrugada, opciones_de_dia
from nucleo.jarvis import Jarvis

INICIO = "Inicio"
AJUSTES = "Ajustes"


@st.cache_resource
def obtener_jarvis():
    return Jarvis()


def elegir_fecha(jarvis):
    hoy, ayer = opciones_de_dia()
    if es_madrugada(datetime.now(), jarvis.leer_config("dia.hora_corte")):
        eleccion = st.sidebar.radio(
            "Es de madrugada: ¿a qué día cuenta lo que registres?",
            ["Ayer (" + ayer + ")", "Hoy (" + hoy + ")"],
        )
        if eleccion.startswith("Ayer"):
            return ayer
        return hoy
    return hoy


def portada(jarvis):
    st.title("Trasno")
    st.caption("Día activo: " + jarvis.fecha_activa)
    resumen = jarvis.resumen_del_dia(jarvis.fecha_activa)
    if len(resumen) == 0:
        st.info("Todavía no hay nada registrado hoy.")
    for modulo, texto in resumen:
        st.write(modulo.icono + " **" + modulo.titulo + ":** " + texto)


def ajustes(jarvis):
    st.title("Ajustes")
    st.subheader("Módulos")
    for nombre in sorted(jarvis.modulos):
        modulo = jarvis.modulos[nombre]
        etiqueta = modulo.icono + " " + modulo.titulo
        if len(modulo.dependencias) > 0:
            etiqueta = etiqueta + " (necesita: " + ", ".join(modulo.dependencias) + ")"
        actual = jarvis.esta_activo(nombre)
        nuevo = st.toggle(etiqueta, value=actual, key="mod_" + nombre)
        if nuevo != actual:
            jarvis.activar(nombre, nuevo)
            st.rerun()
    for carpeta, motivo in jarvis.errores.items():
        st.warning(carpeta + ": " + motivo)

    st.subheader("Registros")
    sobrescribir = st.toggle(
        "Si registro una métrica dos veces el mismo día, sobrescribir",
        value=jarvis.sobrescribir_metricas(),
    )
    if sobrescribir != jarvis.sobrescribir_metricas():
        valor = "0"
        if sobrescribir:
            valor = "1"
        jarvis.guardar_config("metricas.sobrescribir", valor)


def ejecutar():
    st.set_page_config(page_title="Trasno", layout="wide")
    jarvis = obtener_jarvis()
    jarvis.fecha_activa = elegir_fecha(jarvis)

    activos = jarvis.activos()
    por_titulo = {}
    for modulo in activos:
        por_titulo[modulo.icono + " " + modulo.titulo] = modulo

    opciones = [INICIO] + list(por_titulo) + [AJUSTES]
    eleccion = st.sidebar.radio("Menú", opciones)

    if eleccion == INICIO:
        portada(jarvis)
    elif eleccion == AJUSTES:
        ajustes(jarvis)
    else:
        por_titulo[eleccion].pagina(jarvis)
