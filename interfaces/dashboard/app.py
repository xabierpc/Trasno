"""Portada del dashboard: estado de la API y módulos cargados.

Es la página principal; Streamlit añade solo las páginas de `pages/` al menú.
"""

from __future__ import annotations

import httpx
import streamlit as st

from interfaces.dashboard.cliente import API_URL, api_client

st.set_page_config(page_title="Trasno", layout="wide")
st.title("Trasno")

try:
    respuesta = api_client().get("/health")
    respuesta.raise_for_status()
except httpx.HTTPError as error:
    st.error(f"La API no responde en {API_URL}: {error}")
    st.caption("Arráncala con `uv run python main.py`.")
    st.stop()

health = respuesta.json()
st.success(f"API {health['status']} · versión {health['version']}")

st.subheader("Módulos cargados")
if health["modulos"]:
    st.markdown("\n".join(f"- `{nombre}`" for nombre in health["modulos"]))
else:
    st.info("Ningún módulo se ha registrado todavía.")
