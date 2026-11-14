"""Página «Peso»: registrar el peso del día y ver su evolución.

Cliente fino: solo habla con la API de tracking. La media móvil de 7 días se calcula al
pintar (`graficas.py`): es una transformación de presentación, no una regla de negocio.
"""

from __future__ import annotations

from datetime import date, timedelta

import httpx
import streamlit as st

from interfaces.dashboard.cliente import API_URL, api_client
from interfaces.dashboard.fecha import pedir_fecha
from interfaces.dashboard.graficas import grafica_con_media_movil

METRICA = "peso"
DIAS_GRAFICA = 90


st.title("Peso")
cliente = api_client()

try:
    respuesta = cliente.get("/tracking/fecha-logica")
    respuesta.raise_for_status()
except httpx.HTTPError as error:
    st.error(f"La API no responde en {API_URL}: {error}")
    st.stop()
fecha_logica = respuesta.json()

with st.form("registrar_peso"):
    valor = st.number_input("Peso (kg)", min_value=0.0, value=None, step=0.1, format="%.1f")
    dia = pedir_fecha(fecha_logica, "este peso")
    enviado = st.form_submit_button("Guardar")

if enviado and valor is None:
    st.warning("Escribe un peso antes de guardar.")
elif enviado:
    guardado = cliente.post(
        "/tracking/entries",
        json={"metric": METRICA, "valor": valor, "logical_date": dia.isoformat()},
    )
    if guardado.is_success:
        st.success(f"Guardado: {valor:.1f} kg el {dia:%d/%m/%Y}")
    else:
        st.error(guardado.json().get("detail", "No se pudo guardar el peso."))

hoy = date.fromisoformat(fecha_logica["hoy"])
desde = hoy - timedelta(days=DIAS_GRAFICA)
historial = cliente.get(
    "/tracking/entries",
    params={"metric": METRICA, "desde": desde.isoformat(), "hasta": hoy.isoformat()},
)
if not historial.is_success:
    st.error(historial.json().get("detail", "No se pudo leer el historial."))
elif not historial.json():
    st.info("Todavía no hay pesos registrados.")
else:
    puntos = [(date.fromisoformat(e["logical_date"]), float(e["valor"])) for e in historial.json()]
    st.plotly_chart(grafica_con_media_movil(puntos, "Peso", "kg"))
