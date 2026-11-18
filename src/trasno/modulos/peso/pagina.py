"""Pantalla de peso."""

import pandas as pd
import streamlit as st

from trasno.modulos.peso import servicio
from trasno.nucleo.metricas import YaRegistrado

COLUMNAS = ["kg"]


def valor_previo(previo, columna, defecto):
    if previo is None:
        return defecto
    return previo[columna]


def dibujar(jarvis, modulo):
    st.title(modulo.titulo)
    fecha = jarvis.fecha_activa
    previo = servicio.del_dia(jarvis, fecha)

    with st.form("form_peso"):
        st.caption("Registro del " + fecha)
        kg = st.number_input("Peso (kg)", min_value=0.0, step=0.1, value=valor_previo(previo, "kg", 0.0))
        enviado = st.form_submit_button("Guardar")
    if enviado:
        try:
            servicio.registrar(jarvis, fecha, kg)
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
    st.line_chart(tabla[["kg"]])
    st.dataframe(tabla.sort_index(ascending=False))
