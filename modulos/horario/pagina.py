"""Pantalla de horario."""

import streamlit as st


def dibujar(jarvis, modulo):
    st.title(modulo.icono + " " + modulo.titulo)
    st.info("En construcción: horario semanal de clase y trabajo.")
