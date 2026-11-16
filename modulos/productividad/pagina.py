"""Pantalla de productividad."""

import streamlit as st


def dibujar(jarvis, modulo):
    st.title(modulo.icono + " " + modulo.titulo)
    st.info("En construcción: cronómetro por categoría.")
