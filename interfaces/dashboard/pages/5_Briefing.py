"""Página «Briefing»: el resumen del día que prepara Trasno, y un botón para enviarlo ya.

Cliente fino: pide el briefing a `GET /briefing` y lo pinta tal cual (viene en Markdown).
"""

from __future__ import annotations

from datetime import date

import httpx
import streamlit as st

from interfaces.dashboard.cliente import API_URL, api_client

TRABAJO = "briefing.diario"

st.title("Briefing")
cliente = api_client()

try:
    hoy = date.fromisoformat(cliente.get("/briefing").raise_for_status().json()["dia"])
except httpx.HTTPError as error:
    st.error(f"La API no responde en {API_URL}: {error}")
    st.stop()

dia = st.date_input("Día", value=hoy, format="DD/MM/YYYY", key="dia_briefing")
briefing = cliente.get("/briefing", params={"dia": dia.isoformat()}).json()

with st.container(border=True):
    st.markdown(briefing["markdown"])

proxima = {t["nombre"]: t["proxima"] for t in cliente.get("/jobs").json()}.get(TRABAJO)
if proxima:
    st.caption(f"Se envía solo cada día; el próximo, {proxima[:16].replace('T', ' a las ')}.")

if st.button("Enviar la notificación ahora", key="enviar_briefing"):
    respuesta = cliente.post(f"/jobs/{TRABAJO}/run")
    if respuesta.is_success:
        st.success("Briefing enviado.")
    else:
        st.error("No se pudo enviar el briefing.")
