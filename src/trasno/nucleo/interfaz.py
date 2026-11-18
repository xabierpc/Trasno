"""Interfaz Streamlit del nucleo: menu, portada, ajustes y pregunta de madrugada.

Cada carpeta de modulos/ es una pagina propia (st.navigation) con su URL.
El nucleo no conoce ningun modulo concreto: crea una pagina por cada modulo
activo que le da el Jarvis y la pagina llama a modulo.pagina(jarvis).
"""

from datetime import datetime

import streamlit as st

from trasno.nucleo import avisos
from trasno.nucleo.fechas import dia_bonito, es_madrugada, opciones_de_dia
from trasno.nucleo.jarvis import Jarvis

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
    """Inicio: cada modulo activo que implementa inicio() dibuja su bloque en una columna."""
    st.title("Trasno")
    st.caption("Día activo: " + dia_bonito(jarvis.fecha_activa))
    bloques = [m for m in jarvis.activos() if m.tiene_inicio()]
    bloques.sort(key=lambda m: m.orden_inicio)
    if len(bloques) == 0:
        st.info("Ningún módulo activo tiene nada que mostrar aquí. Actívalos en Ajustes.")
        return
    columnas = st.columns(len(bloques), gap="large")
    for columna, modulo in zip(columnas, bloques):
        with columna:
            modulo.inicio(jarvis, jarvis.fecha_activa)


def ajustes(jarvis):
    st.title("Ajustes")
    st.subheader("Módulos")
    for nombre in sorted(jarvis.modulos):
        modulo = jarvis.modulos[nombre]
        etiqueta = modulo.titulo
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


def pagina_de_modulo(jarvis, modulo):
    """Una pagina de Streamlit por carpeta de modulos/, con su propia URL (/<nombre>)."""

    def dibujar():
        modulo.pagina(jarvis)

    return st.Page(dibujar, title=modulo.titulo, icon=modulo.icono or None, url_path=modulo.nombre)


def ejecutar():
    st.set_page_config(page_title="Trasno", layout="wide")
    jarvis = obtener_jarvis()

    inicio = st.Page(lambda: portada(jarvis), title=INICIO, url_path="inicio", default=True)
    pagina_ajustes = st.Page(lambda: ajustes(jarvis), title=AJUSTES, url_path="ajustes")
    paginas_modulos = [pagina_de_modulo(jarvis, modulo) for modulo in jarvis.activos()]

    secciones = {"Trasno": [inicio]}
    if len(paginas_modulos) > 0:
        secciones["Módulos"] = paginas_modulos
    secciones["Sistema"] = [pagina_ajustes]
    navegacion = st.navigation(secciones)

    jarvis.fecha_activa = elegir_fecha(jarvis)
    avisos.mostrar()
    navegacion.run()
