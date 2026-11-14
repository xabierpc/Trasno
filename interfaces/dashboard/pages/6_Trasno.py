"""Página «Trasno»: chat con el agente, con botones para confirmar lo que propone.

Cliente fino: el historial vive en `st.session_state` y se manda entero a `POST /agent/chat` en
cada mensaje (el servidor no guarda conversaciones). Las propuestas se confirman o cancelan con
`POST /agent/confirm`.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import streamlit as st

from interfaces.dashboard.cliente import api_client

TIMEOUT_LLM = 180.0  # un modelo local puede tardar; el cliente compartido espera solo 5 s
NOMBRE_ESTADO = {"ejecutada": "✅ Hecho", "cancelada": "✖️ Cancelado", "fallida": "⚠️ Ha fallado"}


def detalle(respuesta: httpx.Response, por_defecto: str) -> str:
    try:
        return str(respuesta.json().get("detail", por_defecto))
    except ValueError:
        return por_defecto


def argumentos(accion: dict[str, Any]) -> str:
    """{"titulo": "x", "fecha": "2026-11-15"} → «titulo: x · fecha: 2026-11-15»."""

    def texto(valor: Any) -> str:
        return (
            json.dumps(valor, ensure_ascii=False) if isinstance(valor, list | dict) else str(valor)
        )

    return " · ".join(
        f"{clave}: {texto(valor)}"
        for clave, valor in accion["argumentos"].items()
        if valor is not None
    )


def resolver(accion_id: int, aceptar: bool) -> None:
    """Callback de los botones: confirma o cancela y guarda cómo ha quedado."""
    respuesta = api_client().post(
        "/agent/confirm", json={"accion_id": accion_id, "aceptar": aceptar}
    )
    if respuesta.is_success:
        st.session_state["trasno_resueltas"][accion_id] = respuesta.json()
    else:
        st.session_state["trasno_error"] = detalle(respuesta, "No se pudo confirmar.")


def pintar_propuesta(accion: dict[str, Any]) -> None:
    resuelta = st.session_state["trasno_resueltas"].get(accion["id"])
    with st.container(border=True):
        st.markdown(f"**{accion['descripcion'] or accion['herramienta']}**")
        st.caption(argumentos(accion))
        if resuelta is None:
            confirmar, cancelar, _ = st.columns([1, 1, 4])
            confirmar.button(
                "Confirmar",
                type="primary",
                key=f"confirmar-{accion['id']}",
                on_click=resolver,
                args=(accion["id"], True),
            )
            cancelar.button(
                "Cancelar",
                key=f"cancelar-{accion['id']}",
                on_click=resolver,
                args=(accion["id"], False),
            )
        else:
            texto = NOMBRE_ESTADO.get(resuelta["estado"], resuelta["estado"])
            st.markdown(f"{texto}: {resuelta['resultado'] or ''}")


def pintar_mensaje(mensaje: dict[str, Any]) -> None:
    with st.chat_message("user" if mensaje["rol"] == "user" else "assistant"):
        st.markdown(mensaje["contenido"])
        if mensaje.get("ejecutadas"):
            with st.expander(f"Qué he hecho ({len(mensaje['ejecutadas'])})"):
                for accion in mensaje["ejecutadas"]:
                    icono = "⚠️" if accion["estado"] == "fallida" else "✓"
                    st.markdown(f"{icono} `{accion['herramienta']}` · {accion['resultado'] or ''}")
        for accion in mensaje.get("propuestas", []):
            pintar_propuesta(accion)


# --- Página -----------------------------------------------------------------------------------

st.title("Trasno")
estado = st.session_state
estado.setdefault("trasno_mensajes", [])
estado.setdefault("trasno_resueltas", {})

if st.button("Nueva conversación", key="nueva_conversacion"):
    estado["trasno_mensajes"] = []
    estado["trasno_resueltas"] = {}

if not estado["trasno_mensajes"]:
    st.caption("Pídeme cosas como «peso 74,3 y qué tengo hoy» o «añade la tarea X para mañana».")

for mensaje in estado["trasno_mensajes"]:
    pintar_mensaje(mensaje)

if error := estado.pop("trasno_error", None):
    st.error(error)

if texto := st.chat_input("Escribe a Trasno…", key="trasno_entrada"):
    estado["trasno_mensajes"].append({"rol": "user", "contenido": texto})
    pintar_mensaje(estado["trasno_mensajes"][-1])
    historial = [{"rol": m["rol"], "contenido": m["contenido"]} for m in estado["trasno_mensajes"]]
    with st.spinner("Pensando…"):
        try:
            respuesta = api_client().post(
                "/agent/chat", json={"mensajes": historial}, timeout=TIMEOUT_LLM
            )
        except httpx.HTTPError as error:
            respuesta = None
            st.error(f"La API no responde: {error}")
    if respuesta is not None and respuesta.is_success:
        datos = respuesta.json()
        estado["trasno_mensajes"].append(
            {
                "rol": "assistant",
                "contenido": datos["respuesta"] or "_(sin respuesta)_",
                "ejecutadas": datos["ejecutadas"],
                "propuestas": datos["propuestas"],
            }
        )
        st.rerun()
    elif respuesta is not None:
        estado["trasno_mensajes"].pop()  # el mensaje no se ha contestado: se puede repetir
        st.error(detalle(respuesta, "El agente no ha podido responder."))
