"""Pantalla de dieta: lista semanal de lo que se puede comer y lo que no.

El bloque de Inicio muestra la semana del dia activo; la pagina permite
moverse entre semanas. Solo presentacion: todo pasa por servicio.
"""

from datetime import timedelta

import streamlit as st

from trasno.modulos.dieta import servicio
from trasno.nucleo import avisos
from trasno.nucleo.fechas import a_fecha, dia_bonito

CLAVE_SEMANA = "dieta_lunes"


def dibujar(jarvis, modulo):
    st.title(modulo.titulo)
    actual = servicio.lunes_de_texto(jarvis.fecha_activa)
    lunes = st.session_state.get(CLAVE_SEMANA, actual)

    izquierda, centro, derecha = st.columns([1, 3, 1])
    if izquierda.button("← Anterior", use_container_width=True):
        st.session_state[CLAVE_SEMANA] = (a_fecha(lunes) - timedelta(days=7)).isoformat()
        st.rerun()
    domingo = (a_fecha(lunes) + timedelta(days=6)).isoformat()
    texto = "Semana del " + dia_bonito(lunes) + " al " + dia_bonito(domingo)
    if lunes == actual:
        texto = texto + " (esta semana)"
    centro.markdown("<div style='text-align:center'><b>" + texto + "</b></div>", unsafe_allow_html=True)
    if derecha.button("Siguiente →", use_container_width=True):
        st.session_state[CLAVE_SEMANA] = (a_fecha(lunes) + timedelta(days=7)).isoformat()
        st.rerun()

    lista_semana(jarvis, lunes, "pag")


def bloque_inicio(jarvis, fecha):
    st.subheader("Comida de la semana")
    lista_semana(jarvis, servicio.lunes_de_texto(fecha), "ini")


def lista_semana(jarvis, lunes, prefijo):
    datos = servicio.semana(jarvis, lunes)
    vacia = len(datos["si"]) == 0 and len(datos["no"]) == 0
    if vacia:
        anterior = servicio.semana_anterior_con_datos(jarvis, lunes)
        if anterior is not None:
            if st.button("Copiar lista de la semana del " + dia_bonito(anterior), key=prefijo + "_copiar_" + lunes):
                servicio.copiar_de(jarvis, anterior, lunes)
                st.rerun()

    st.markdown("**✅ Puedo comer**")
    _lista(jarvis, datos["si"], prefijo)
    _campo(jarvis, lunes, True, prefijo)

    st.markdown("**❌ No puedo comer**")
    _lista(jarvis, datos["no"], prefijo)
    _campo(jarvis, lunes, False, prefijo)


def _lista(jarvis, filas, prefijo):
    for fila in filas:
        texto, boton = st.columns([6, 1], vertical_alignment="center")
        texto.write(fila["nombre"])
        boton.button("✕", key=prefijo + "_borrar_" + str(fila["id"]), help="Quitar",
                     on_click=servicio.borrar, args=(jarvis, fila["id"]))


def _campo(jarvis, lunes, permitido, prefijo):
    clave = prefijo + "_nuevo_" + ("si_" if permitido else "no_") + lunes
    st.text_input(
        "Nuevo alimento", key=clave, label_visibility="collapsed",
        placeholder="+ Añadir (Enter)",
        on_change=_anadir, args=(jarvis, lunes, permitido, clave),
    )


def _anadir(jarvis, lunes, permitido, clave):
    """Callback del campo: se dispara al pulsar Enter."""
    nombre = st.session_state[clave]
    if nombre.strip() == "":
        return
    try:
        servicio.anadir(jarvis, lunes, nombre, permitido)
    except ValueError as error:
        avisos.avisar("error", str(error))
    st.session_state[clave] = ""
