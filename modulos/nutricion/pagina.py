"""Pantalla de nutricion."""

import pandas as pd
import streamlit as st

from modulos.nutricion import servicio
from nucleo.metricas import YaRegistrado

COLUMNAS = ["kcal", "proteina_g", "carbohidratos_g", "grasas_g"]


def valor_previo(previo, columna, defecto):
    if previo is None:
        return defecto
    return previo[columna]


def dibujar(jarvis, modulo):
    st.title(modulo.titulo)
    fecha = jarvis.fecha_activa
    previo = servicio.del_dia(jarvis, fecha)

    with st.form("form_nutricion"):
        st.caption("Registro del " + fecha)
        kcal = st.number_input("Kcal", min_value=0.0, step=10.0, value=valor_previo(previo, "kcal", 0.0))
        proteina_g = st.number_input("Proteína (g)", min_value=0.0, step=1.0, value=valor_previo(previo, "proteina_g", 0.0))
        carbohidratos_g = st.number_input("Carbohidratos (g)", min_value=0.0, step=1.0, value=valor_previo(previo, "carbohidratos_g", 0.0))
        grasas_g = st.number_input("Grasas (g)", min_value=0.0, step=1.0, value=valor_previo(previo, "grasas_g", 0.0))
        enviado = st.form_submit_button("Guardar")
    if enviado:
        try:
            servicio.registrar(jarvis, fecha, kcal, proteina_g, carbohidratos_g, grasas_g)
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
    st.line_chart(tabla[["kcal"]])
    st.dataframe(tabla.sort_index(ascending=False))
