"""Mensajes que sobreviven a un st.rerun().

Una pagina guarda algo, llama a avisar(...) y hace st.rerun() para que todas
las pestanas se vuelvan a dibujar con los datos nuevos. El marco del nucleo
llama a mostrar() al principio de cada ejecucion y los ensena.
"""

import streamlit as st

CLAVE = "_avisos_pendientes"


def avisar(tipo, texto):
    """tipo: 'exito', 'aviso' o 'error'."""
    if CLAVE not in st.session_state:
        st.session_state[CLAVE] = []
    st.session_state[CLAVE].append((tipo, texto))


def mostrar():
    pendientes = st.session_state.pop(CLAVE, [])
    for tipo, texto in pendientes:
        if tipo == "exito":
            st.success(texto)
        elif tipo == "aviso":
            st.warning(texto)
        else:
            st.error(texto)
