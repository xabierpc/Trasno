"""Selector de fecha lógica compartido por las páginas que registran datos de un día."""

from __future__ import annotations

from datetime import date

import streamlit as st


def pedir_fecha(fecha_logica: dict[str, object], que: str = "este registro") -> date:
    """Pide el día al que cuenta el registro; de madrugada pregunta «¿ayer u hoy?».

    `fecha_logica` es la respuesta de GET /tracking/fecha-logica y `que` completa la pregunta.
    """
    ayer = date.fromisoformat(str(fecha_logica["ayer"]))
    hoy = date.fromisoformat(str(fecha_logica["hoy"]))
    if not fecha_logica["es_madrugada"]:
        return st.date_input("Fecha", value=hoy, max_value=hoy, format="DD/MM/YYYY")
    eleccion = st.radio(
        f"Es de madrugada: ¿a qué día cuenta {que}?",
        options=[ayer, hoy],
        format_func=lambda d: f"{'Ayer' if d == ayer else 'Hoy'} ({d:%d/%m})",
        horizontal=True,
    )
    return eleccion or ayer
