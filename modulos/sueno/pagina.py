"""Pantalla de sueno."""

import pandas as pd
import streamlit as st

from modulos.sueno import servicio
from nucleo.metricas import YaRegistrado

COLUMNAS = ["horas", "calidad"]


def valor_previo(previo, columna, defecto):
    if previo is None:
        return defecto
    return previo[columna]


def dibujar(jarvis, modulo):
    st.title(modulo.icono + " " + modulo.titulo)
    fecha = jarvis.fecha_activa
    previo = servicio.del_dia(jarvis, fecha)

    with st.form("form_sueno"):
        st.caption("Registro del " + fecha)
        horas = st.number_input("Horas dormidas", min_value=0.0, step=0.25, value=valor_previo(previo, "horas", 0.0))
        calidad = st.number_input("Calidad (1-5)", min_value=1, step=1, value=int(valor_previo(previo, "calidad", 1)))
        enviado = st.form_submit_button("Guardar")
    if enviado:
        try:
            servicio.registrar(jarvis, fecha, horas, calidad)
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
    st.line_chart(tabla[["horas"]])
    st.dataframe(tabla.sort_index(ascending=False))
