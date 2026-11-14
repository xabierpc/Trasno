"""Página «Registro diario»: todas las métricas activas en un solo formulario.

Cliente fino: solo habla con la API de tracking. Cada campo se pinta según el tipo de la
métrica y arranca con lo ya registrado ese día; al guardar solo se envía lo que ha cambiado.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import httpx
import streamlit as st

from interfaces.dashboard.cliente import API_URL, api_client
from interfaces.dashboard.fecha import pedir_fecha

Metrica = dict[str, Any]
COLUMNAS_HABITOS = 3


def detalle(respuesta: httpx.Response, por_defecto: str) -> str:
    """Mensaje de error de la API, o `por_defecto` si no lo trae."""
    try:
        return str(respuesta.json().get("detail", por_defecto))
    except ValueError:
        return por_defecto


def valor_del_dia(cliente: httpx.Client, metrica: Metrica, dia: date) -> Any:
    """Valor ya registrado ese día, o None (las `keep_all` acumulan: siempre empiezan vacías)."""
    if metrica["on_duplicate"] != "replace":
        return None
    respuesta = cliente.get(
        "/tracking/entries",
        params={"metric": metrica["nombre"], "desde": dia.isoformat(), "hasta": dia.isoformat()},
    )
    entradas = respuesta.json() if respuesta.is_success else []
    return entradas[-1]["valor"] if entradas else None


def etiqueta(metrica: Metrica) -> str:
    nombre = str(metrica["nombre"]).capitalize()
    if metrica["tipo"] == "duracion":
        return f"{nombre} (horas)"
    return f"{nombre} ({metrica['unidad']})" if metrica["unidad"] else nombre


def campo(metrica: Metrica, actual: Any, dia: date) -> Any:
    """Pinta el campo de la métrica y devuelve su valor listo para la API (None = vacío)."""
    clave = f"{metrica['nombre']}-{dia.isoformat()}"
    texto = etiqueta(metrica)
    match metrica["tipo"]:
        case "booleana":
            return st.checkbox(texto, value=bool(actual), key=clave)
        case "categorica":
            opciones = metrica["categorias"]
            indice = opciones.index(actual) if actual in opciones else None
            return st.selectbox(texto, opciones, index=indice, key=clave)
        case "numerica":
            return st.number_input(
                texto,
                min_value=metrica["minimo"],
                max_value=metrica["maximo"],
                value=actual,
                step=0.1,
                format="%.1f",
                key=clave,
            )
        case "duracion":
            # Se guarda en minutos, pero un sueño de «7,5 horas» se escribe más rápido.
            horas = st.number_input(
                texto,
                min_value=0.0,
                value=None if actual is None else actual / 60,
                step=0.25,
                format="%.2f",
                key=clave,
            )
            return None if horas is None else round(horas * 60)
        case "escala":
            return st.number_input(
                texto, min_value=1, max_value=metrica["escala_max"], value=actual, key=clave
            )
        case _:  # conteo
            return st.number_input(texto, min_value=0, value=actual, step=1, key=clave)


def ha_cambiado(metrica: Metrica, nuevo: Any, actual: Any) -> bool:
    """Indica si hay que enviar el campo: tiene valor y no es el que ya estaba guardado."""
    if metrica["tipo"] == "booleana":
        return nuevo != bool(actual) if actual is not None else bool(nuevo)
    return nuevo is not None and nuevo != actual


def tabla_rachas(cliente: httpx.Client, metricas: list[Metrica], dia: date) -> list[dict[str, Any]]:
    """Filas de racha y cumplimiento de los hábitos y de las métricas con objetivo."""
    filas = []
    for metrica in metricas:
        if metrica["tipo"] != "booleana" and metrica["objetivo"] is None:
            continue
        respuesta = cliente.get(
            f"/tracking/metrics/{metrica['nombre']}/racha", params={"hoy": dia.isoformat()}
        )
        if not respuesta.is_success:
            continue
        racha = respuesta.json()
        filas.append(
            {
                "Métrica": str(metrica["nombre"]).capitalize(),
                "Racha": racha["actual"],
                "Máxima": racha["maxima"],
                "7 días": f"{racha['semanal']['cumplidos']}/{racha['semanal']['dias']}",
                "30 días": f"{racha['mensual']['cumplidos']}/{racha['mensual']['dias']}",
            }
        )
    return filas


st.title("Registro diario")
cliente = api_client()

try:
    respuesta = cliente.get("/tracking/fecha-logica")
    respuesta.raise_for_status()
    todas: list[Metrica] = cliente.get("/tracking/metrics").raise_for_status().json()
except httpx.HTTPError as error:
    st.error(f"La API no responde en {API_URL}: {error}")
    st.stop()

# Fuera del formulario: al cambiar de día los campos se rellenan con lo de ese día.
dia = pedir_fecha(respuesta.json(), "este registro")
metricas = [m for m in todas if m["activa"]]

if not metricas:
    st.info("No hay métricas activas. Actívalas abajo, en «Métricas activas».")
else:
    actuales = {m["nombre"]: valor_del_dia(cliente, m, dia) for m in metricas}
    habitos = [m for m in metricas if m["tipo"] == "booleana"]
    with st.form("registro_diario"):
        valores = {
            m["nombre"]: campo(m, actuales[m["nombre"]], dia)
            for m in metricas
            if m["tipo"] != "booleana"
        }
        if habitos:
            st.subheader("Hábitos")
            for indice, columna in enumerate(st.columns(COLUMNAS_HABITOS)):
                with columna:
                    for m in habitos[indice::COLUMNAS_HABITOS]:
                        valores[m["nombre"]] = campo(m, actuales[m["nombre"]], dia)
        enviado = st.form_submit_button("Guardar")

    if enviado:
        cambios = [
            m for m in metricas if ha_cambiado(m, valores[m["nombre"]], actuales[m["nombre"]])
        ]
        guardadas = []
        for m in cambios:
            cuerpo = {
                "metric": m["nombre"],
                "valor": valores[m["nombre"]],
                "logical_date": dia.isoformat(),
            }
            guardado = cliente.post("/tracking/entries", json=cuerpo)
            if guardado.is_success:
                guardadas.append(m["nombre"])
            else:
                st.error(f"{m['nombre']}: {detalle(guardado, 'no se pudo guardar')}")
        if guardadas:
            st.success(f"Guardado el {dia:%d/%m/%Y}: {', '.join(guardadas)}")
        elif not cambios:
            st.warning("No hay nada nuevo que guardar.")

    rachas = tabla_rachas(cliente, metricas, dia)
    if rachas:
        st.subheader("Rachas")
        st.dataframe(rachas, hide_index=True)

with st.expander("Métricas activas"):
    st.caption("Desactivar una métrica la quita de este formulario; sus datos se conservan.")
    for m in todas:
        activa = st.checkbox(
            str(m["nombre"]).capitalize(), value=m["activa"], key=f"activa-{m['nombre']}"
        )
        if activa != m["activa"]:
            cambio = cliente.patch(f"/tracking/metrics/{m['nombre']}", json={"activa": activa})
            if cambio.is_success:
                st.rerun()
            st.error(detalle(cambio, "No se pudo cambiar la métrica."))
