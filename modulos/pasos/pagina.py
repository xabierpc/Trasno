"""Pantalla de pasos."""

import pandas as pd
import streamlit as st

from modulos.pasos import servicio
from nucleo.metricas import YaRegistrado

COLUMNAS = ["pasos"]


def valor_previo(previo, columna, defecto):
    if previo is None:
        return defecto
    return previo[columna]


def dibujar(jarvis, modulo):
    st.title(modulo.icono + " " + modulo.titulo)
    fecha = jarvis.fecha_activa
    previo = servicio.del_dia(jarvis, fecha)

    with st.form("form_pasos"):
        st.caption("Registro del " + fecha)
        pasos = st.number_input("Pasos", min_value=0, step=100, value=int(valor_previo(previo, "pasos", 0)))
        enviado = st.form_submit_button("Guardar")
    if enviado:
        try:
            servicio.registrar(jarvis, fecha, pasos)
            st.success("Guardado")
        except YaRegistrado:
            st.warning("Ya había un registro ese día y en Ajustes está desactivado sobrescribir.")
        except ValueError as error:
            st.error(str(error))

    filas = servicio.historial(jarvis)
    if len(filas) == 0:
        st.info("Sin registros todavía.")
        return
    tabla = pd.DataFrame([dict(fila) for fila in filas])[["fecha"] + COLUMNAS].set_index("fecha")
    st.line_chart(tabla[["pasos"]])
    st.dataframe(tabla.sort_index(ascending=False))
