"""Cliente httpx compartido por todas las páginas del dashboard.

Uso en una página:

    from interfaces.dashboard.cliente import api_client

    respuesta = api_client().get("/tracking/metricas")
"""

from __future__ import annotations

import httpx
import streamlit as st

API_URL = "http://127.0.0.1:8000"
TIMEOUT_SEGUNDOS = 5.0


@st.cache_resource
def api_client() -> httpx.Client:
    """Devuelve el cliente de la API, creado una sola vez por proceso de Streamlit."""
    return _crear_cliente()


def _crear_cliente() -> httpx.Client:
    return httpx.Client(base_url=API_URL, timeout=TIMEOUT_SEGUNDOS)
