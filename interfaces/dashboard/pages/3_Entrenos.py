"""Página «Entrenos»: registrar una sesión en una sola pantalla y ver la progresión.

Cliente fino: solo habla con la API (training, y tracking para la fecha lógica). Cada fila del
formulario son N series iguales de un ejercicio: «press banca · 3 · 8 · 60» se escribe una vez.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import httpx
import streamlit as st

from interfaces.dashboard.cliente import API_URL, api_client
from interfaces.dashboard.entrenos import FilaEntreno, ejercicios_de_filas, resumen_ejercicio
from interfaces.dashboard.fecha import pedir_fecha
from interfaces.dashboard.graficas import grafica_progreso_1rm, grafica_volumen_semanal

FILAS_INICIALES = 4
SERIES_POR_DEFECTO = 3
SEMANAS_GRAFICA = 12
SESIONES_RECIENTES = 10
NOMBRE_RECORD = {"peso": "peso", "1rm": "1RM estimado", "volumen": "volumen"}


def detalle(respuesta: httpx.Response, por_defecto: str) -> str:
    """Mensaje de error de la API, o `por_defecto` si no lo trae."""
    try:
        return str(respuesta.json().get("detail", por_defecto))
    except ValueError:
        return por_defecto


def leer(cliente: httpx.Client, ruta: str, **params: str) -> Any:
    """GET que devuelve el JSON, o None (avisando) si la API responde con error."""
    respuesta = cliente.get(ruta, params=params)
    if respuesta.is_success:
        return respuesta.json()
    st.error(detalle(respuesta, f"No se pudo leer {ruta}."))
    return None


def fila(numero: int, version: int, conocidos: list[str]) -> FilaEntreno:
    """Pinta una fila del formulario y devuelve lo que el usuario ha escrito en ella."""
    visible = "visible" if numero == 0 else "collapsed"  # las etiquetas solo en la primera fila
    ejercicio, series, reps, peso, rpe = st.columns([4, 1.2, 1.2, 1.5, 1.2])
    clave = f"{version}-{numero}"
    return FilaEntreno(
        ejercicio=ejercicio.selectbox(
            "Ejercicio",
            conocidos,
            index=None,
            placeholder="Elige o escribe uno nuevo",
            accept_new_options=True,
            label_visibility=visible,
            key=f"ejercicio-{clave}",
        ),
        series=series.number_input(
            "Series",
            min_value=1,
            value=SERIES_POR_DEFECTO,
            label_visibility=visible,
            key=f"series-{clave}",
        ),
        reps=reps.number_input(
            "Reps", min_value=1, value=None, label_visibility=visible, key=f"reps-{clave}"
        ),
        peso=peso.number_input(
            "Peso (kg)",
            min_value=0.0,
            value=None,
            step=2.5,
            format="%g",
            help="Vacío = peso corporal (0 kg).",
            label_visibility=visible,
            key=f"peso-{clave}",
        ),
        rpe=rpe.number_input(
            "RPE",
            min_value=1.0,
            max_value=10.0,
            value=None,
            step=0.5,
            format="%g",
            label_visibility=visible,
            key=f"rpe-{clave}",
        ),
    )


def aviso_de_guardado(sesion: dict[str, Any]) -> None:
    """Confirma la sesión guardada y celebra los récords que haya batido."""
    dia = date.fromisoformat(sesion["logical_date"])
    st.success(f"Sesión de {sesion['tipo']} guardada el {dia:%d/%m/%Y} · {sesion['volumen']:g} kg")
    for record in sesion["records"]:
        st.info(
            f"Nuevo récord de {NOMBRE_RECORD[record['tipo']]} en {record['ejercicio']}: "
            f"{record['valor']:g} kg (antes {record['anterior']:g})"
        )


st.title("Entrenos")
cliente = api_client()

try:
    fecha_logica = cliente.get("/tracking/fecha-logica").raise_for_status().json()
    conocidos: list[str] = cliente.get("/training/exercises").raise_for_status().json()
except httpx.HTTPError as error:
    st.error(f"La API no responde en {API_URL}: {error}")
    st.stop()

estado = st.session_state
estado.setdefault("entreno_filas", FILAS_INICIALES)
estado.setdefault("entreno_version", 0)  # cambia tras guardar para vaciar el formulario
if "entreno_guardado" in estado:
    aviso_de_guardado(estado.pop("entreno_guardado"))

# --- Registrar una sesión --------------------------------------------------------------

with st.form("registrar_entreno"):
    version = estado["entreno_version"]
    c_fecha, c_tipo, c_duracion, c_energia = st.columns([2, 2, 1.5, 1.5])
    with c_fecha:
        dia = pedir_fecha(fecha_logica, "este entreno")
    tipo = c_tipo.text_input("Tipo", value="fuerza", key=f"tipo-{version}")
    duracion = c_duracion.number_input(
        "Duración (min)", min_value=1, value=None, key=f"duracion-{version}"
    )
    energia = c_energia.number_input(
        "Energía previa (1-10)", min_value=1, max_value=10, value=None, key=f"energia-{version}"
    )
    filas = [fila(numero, version, conocidos) for numero in range(estado["entreno_filas"])]
    enviado = st.form_submit_button("Guardar sesión", type="primary", key="guardar_sesion")

if st.button("Añadir fila", key="añadir_fila"):
    estado["entreno_filas"] += 1
    st.rerun()

if enviado:
    ejercicios, errores = ejercicios_de_filas(filas)
    for error in errores:
        st.warning(error)
    if not errores:
        cuerpo = {
            "logical_date": dia.isoformat(),
            "tipo": tipo,
            "duracion_min": duracion,
            "energia_previa": energia,
            "ejercicios": ejercicios,
        }
        guardado = cliente.post("/training/sessions", json=cuerpo)
        if guardado.is_success:
            estado["entreno_guardado"] = guardado.json()
            estado["entreno_version"] += 1
            estado["entreno_filas"] = FILAS_INICIALES
            st.rerun()
        st.error(detalle(guardado, "No se pudo guardar la sesión."))

# --- Progresión ------------------------------------------------------------------------

hoy = date.fromisoformat(fecha_logica["hoy"])

st.subheader("Progresión de 1RM")
if not conocidos:
    st.info("Todavía no hay ejercicios registrados.")
else:
    elegido = st.selectbox("Ejercicio", conocidos, key="ejercicio_grafica")
    progreso = leer(cliente, f"/training/exercises/{elegido}/progress") or []
    if progreso:
        puntos = [(date.fromisoformat(p["logical_date"]), p["un_rm"]) for p in progreso]
        st.plotly_chart(grafica_progreso_1rm(puntos, elegido), key="grafica_1rm")
        mejor = max(progreso, key=lambda p: p["un_rm"])
        st.caption(
            f"Mejor 1RM estimado: {mejor['un_rm']:.1f} kg "
            f"({date.fromisoformat(mejor['logical_date']):%d/%m/%Y}) · "
            f"peso máximo: {max(p['peso_maximo'] for p in progreso):g} kg"
        )

st.subheader("Volumen semanal")
desde = hoy - timedelta(weeks=SEMANAS_GRAFICA)
semanas = leer(cliente, "/training/weekly-volume", desde=desde.isoformat()) or []
if semanas:
    barras = [(date.fromisoformat(s["semana"]), s["volumen"]) for s in semanas]
    st.plotly_chart(grafica_volumen_semanal(barras), key="grafica_volumen")
else:
    st.info(f"No hay sesiones con carga en las últimas {SEMANAS_GRAFICA} semanas.")

# --- Últimas sesiones ------------------------------------------------------------------

st.subheader("Últimas sesiones")
sesiones = (leer(cliente, "/training/sessions", desde=desde.isoformat()) or [])[::-1]
recientes = sesiones[:SESIONES_RECIENTES]
if not recientes:
    st.info("Todavía no hay sesiones registradas.")
else:
    st.dataframe(
        [
            {
                "Fecha": date.fromisoformat(s["logical_date"]).strftime("%d/%m/%Y"),
                "Tipo": s["tipo"],
                "Min": s["duracion_min"],
                "Energía": s["energia_previa"],
                "Volumen (kg)": s["volumen"],
                "Ejercicios": " · ".join(resumen_ejercicio(e) for e in s["ejercicios"]),
            }
            for s in recientes
        ],
        hide_index=True,
    )
    with st.expander("Borrar una sesión"):
        a_borrar = st.selectbox(
            "Sesión",
            recientes,
            index=None,
            format_func=lambda s: (
                f"{date.fromisoformat(s['logical_date']):%d/%m/%Y} · {s['tipo']} · "
                f"{s['volumen']:g} kg"
            ),
            key="sesion_a_borrar",
        )
        if st.button("Borrar", disabled=a_borrar is None, key="borrar_sesion") and a_borrar:
            borrado = cliente.delete(f"/training/sessions/{a_borrar['id']}")
            if borrado.is_success:
                st.rerun()
            st.error(detalle(borrado, "No se pudo borrar la sesión."))
