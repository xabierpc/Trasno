"""Página «Mañana»: la agenda de un día (mañana por defecto), sus tareas y el horario semanal.

Cliente fino: solo habla con la API de planning. Las acciones (marcar, mover, crear) se hacen
en callbacks y la página se vuelve a pintar con lo que devuelva la API.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any

import httpx
import streamlit as st

from interfaces.dashboard.cliente import API_URL, api_client

DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
PRIORIDADES = ["alta", "media", "baja"]
ICONO_PRIORIDAD = {"alta": "🔴", "media": "🟡", "baja": "⚪"}


def detalle(respuesta: httpx.Response, por_defecto: str) -> str:
    """Mensaje de error de la API, o `por_defecto` si no lo trae."""
    try:
        return str(respuesta.json().get("detail", por_defecto))
    except ValueError:
        return por_defecto


def avisar(tipo: str, texto: str) -> None:
    """Guarda un aviso para enseñarlo al volver a pintar la página."""
    st.session_state.setdefault("planning_avisos", []).append((tipo, texto))


def llamar(metodo: str, ruta: str, ok: str | None = None, **kwargs: Any) -> Any:
    """Llama a la API; avisa del error si falla. Devuelve el JSON (o None)."""
    respuesta = api_client().request(metodo, ruta, **kwargs)
    if not respuesta.is_success:
        avisar("error", detalle(respuesta, f"La API ha fallado en {ruta}."))
        return None
    if ok:
        avisar("success", ok)
    return respuesta.json() if respuesta.content else None


def avisar_solapes(guardado: dict[str, Any] | None) -> None:
    for aviso in (guardado or {}).get("avisos", []):
        inicio = datetime.fromisoformat(aviso["inicio"])
        avisar("warning", f"Se pisa con «{aviso['titulo']}» ({inicio:%d/%m %H:%M})")


def hora(texto: str) -> str:
    return datetime.fromisoformat(texto).strftime("%H:%M")


# --- Callbacks --------------------------------------------------------------------------------


def cambiar_tarea(tarea_id: str) -> None:
    accion = "complete" if st.session_state[f"tarea-{tarea_id}"] else "reopen"
    llamar("POST", f"/planning/tasks/{tarea_id}/{accion}")


def mover_tarea(tarea_id: str, dia: date) -> None:
    llamar("POST", f"/planning/tasks/{tarea_id}/move", json={"fecha": dia.isoformat()})


def borrar_bloque(bloque_id: str) -> None:
    llamar("DELETE", f"/planning/blocks/{bloque_id}", ok="Bloque borrado.")


# --- Página -----------------------------------------------------------------------------------

st.title("Mañana")
estado = st.session_state

try:
    hoy = date.fromisoformat(api_client().get("/planning/agenda").raise_for_status().json()["dia"])
except httpx.HTTPError as error:
    st.error(f"La API no responde en {API_URL}: {error}")
    st.stop()

eleccion = st.radio("Día", ["Hoy", "Mañana", "Otro"], index=1, horizontal=True, key="dia")
if eleccion == "Hoy":
    dia = hoy
elif eleccion == "Mañana":
    dia = hoy + timedelta(days=1)
else:
    dia = st.date_input("Elige el día", value=hoy, format="DD/MM/YYYY", key="otro_dia")

agenda = llamar("GET", "/planning/agenda", params={"dia": dia.isoformat()})
for tipo, texto in estado.pop("planning_avisos", []):  # los de la acción anterior y este GET
    getattr(st, tipo)(texto)
if agenda is None:
    st.stop()

st.subheader(f"{DIAS_SEMANA[dia.weekday()]} {dia:%d/%m/%Y}")

# --- Horario del día ---

st.markdown("#### Horario")
if not agenda["citas"]:
    st.info("Nada con hora este día.")
for cita in agenda["citas"]:
    lugar = f" · {cita['lugar']}" if cita["lugar"] else ""
    etiqueta = " _(clase)_" if cita["tipo"] == "bloque" else ""
    st.markdown(f"**{hora(cita['inicio'])}-{hora(cita['fin'])}** {cita['titulo']}{lugar}{etiqueta}")

# --- Tareas ---

st.markdown("#### Tareas")
if not agenda["tareas"]:
    st.info("No hay tareas para este día.")
for tarea in agenda["tareas"]:
    estimacion = f" · {tarea['estimacion_min']} min" if tarea["estimacion_min"] else ""
    st.checkbox(
        f"{ICONO_PRIORIDAD[tarea['prioridad']]} {tarea['titulo']}{estimacion}",
        value=tarea["estado"] == "hecha",
        key=f"tarea-{tarea['id']}",
        on_change=cambiar_tarea,
        args=(tarea["id"],),
    )

if agenda["atrasadas"]:
    st.markdown("#### Atrasadas")
    for tarea in agenda["atrasadas"]:
        texto, boton = st.columns([4, 1])
        texto.markdown(f"{tarea['titulo']} _({date.fromisoformat(tarea['fecha']):%d/%m})_")
        boton.button(
            f"Pasar al {dia:%d/%m}",
            key=f"mover-{tarea['id']}",
            on_click=mover_tarea,
            args=(tarea["id"], dia),
        )

with st.form("nueva_tarea", clear_on_submit=True):
    st.markdown("**Nueva tarea**")
    titulo, prioridad, estimacion = st.columns([4, 1.5, 1.5])
    t_titulo = titulo.text_input("Título", key="tarea_titulo")
    t_prioridad = prioridad.selectbox("Prioridad", PRIORIDADES, index=1, key="tarea_prioridad")
    t_estimacion = estimacion.number_input(
        "Minutos", min_value=1, value=None, key="tarea_estimacion"
    )
    if st.form_submit_button("Añadir tarea", key="crear_tarea"):
        llamar(
            "POST",
            "/planning/tasks",
            ok=f"Tarea añadida al {dia:%d/%m}.",
            json={
                "titulo": t_titulo,
                "fecha": dia.isoformat(),
                "prioridad": t_prioridad,
                "estimacion_min": t_estimacion,
            },
        )
        st.rerun()

with st.expander("Nuevo evento"), st.form("nuevo_evento", clear_on_submit=True):
    titulo, inicio, fin, lugar = st.columns([3, 1.5, 1.5, 2])
    e_titulo = titulo.text_input("Título", key="evento_titulo")
    e_inicio = inicio.time_input("Empieza", value=time(9), step=900, key="evento_inicio")
    e_fin = fin.time_input("Termina", value=time(10), step=900, key="evento_fin")
    e_lugar = lugar.text_input("Lugar", key="evento_lugar")
    if st.form_submit_button("Añadir evento", key="crear_evento"):
        guardado = llamar(
            "POST",
            "/planning/events",
            ok=f"Evento añadido al {dia:%d/%m}.",
            json={
                "titulo": e_titulo,
                "inicio": datetime.combine(dia, e_inicio).isoformat(),
                "fin": datetime.combine(dia, e_fin).isoformat(),
                "lugar": e_lugar or None,
            },
        )
        avisar_solapes(guardado)
        st.rerun()

# --- Horario semanal ---

with st.expander("Clases y bloques semanales"):
    for bloque in llamar("GET", "/planning/blocks") or []:
        texto, boton = st.columns([4, 1])
        texto.markdown(
            f"**{DIAS_SEMANA[bloque['dia_semana']]}** {bloque['hora_inicio'][:5]}-"
            f"{bloque['hora_fin'][:5]} {bloque['titulo']}"
        )
        boton.button(
            "Borrar", key=f"borrar-{bloque['id']}", on_click=borrar_bloque, args=(bloque["id"],)
        )
    with st.form("nuevo_bloque", clear_on_submit=True):
        titulo, dia_semana, inicio, fin = st.columns([3, 2, 1.5, 1.5])
        b_titulo = titulo.text_input("Título", key="bloque_titulo")
        b_dia = dia_semana.selectbox(
            "Día", range(7), format_func=DIAS_SEMANA.__getitem__, key="bloque_dia"
        )
        b_inicio = inicio.time_input("Empieza", value=time(9), step=900, key="bloque_inicio")
        b_fin = fin.time_input("Termina", value=time(11), step=900, key="bloque_fin")
        if st.form_submit_button("Añadir bloque", key="crear_bloque"):
            guardado = llamar(
                "POST",
                "/planning/blocks",
                ok="Bloque añadido.",
                json={
                    "titulo": b_titulo,
                    "dia_semana": b_dia,
                    "hora_inicio": b_inicio.isoformat(),
                    "hora_fin": b_fin.isoformat(),
                },
            )
            for pisado in (guardado or {}).get("avisos", []):
                avisar("warning", f"Se pisa con «{pisado['titulo']}»")
            st.rerun()
