"""Router FastAPI del agente: chat, confirmación de acciones y log."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from agent.agente import AccionNoPendiente, Agente
from agent.mensajes import ErrorLLM, Mensaje, Rol
from core.contracts import Accion, EstadoAccion, RegistroAcciones, Tool


class MensajeEntrada(BaseModel):
    """Un mensaje del historial que guarda el cliente (solo usuario y asistente)."""

    rol: Literal["user", "assistant"]
    contenido: str


class ChatEntrada(BaseModel):
    """Cuerpo de POST /agent/chat: la conversación entera; el último mensaje es del usuario."""

    mensajes: list[MensajeEntrada] = Field(min_length=1)


class AccionSalida(BaseModel):
    id: int
    herramienta: str
    descripcion: str
    argumentos: dict[str, Any]
    estado: EstadoAccion
    resultado: str | None
    timestamp: datetime


class ChatSalida(BaseModel):
    """Respuesta del agente, lo que ha hecho y lo que espera confirmación."""

    respuesta: str
    ejecutadas: list[AccionSalida]
    propuestas: list[AccionSalida]


class ConfirmarEntrada(BaseModel):
    accion_id: int
    aceptar: bool = True


class HerramientaSalida(BaseModel):
    nombre: str
    descripcion: str
    requiere_confirmacion: bool
    sensible: bool


def crear_router(
    agente: Agente,
    herramientas: Callable[[], Sequence[Tool]],
    acciones: Callable[[], RegistroAcciones],
) -> APIRouter:
    router = APIRouter(prefix="/agent", tags=["agent"])

    def salida(accion: Accion) -> AccionSalida:
        descripciones = {t.nombre: t.descripcion for t in herramientas()}
        assert accion.id is not None  # las acciones guardadas siempre tienen id
        return AccionSalida(
            id=accion.id,
            herramienta=accion.herramienta,
            descripcion=descripciones.get(accion.herramienta, ""),
            argumentos=accion.argumentos,
            estado=accion.estado,
            resultado=accion.resultado,
            timestamp=accion.timestamp,
        )

    @router.post("/chat")
    def chat(datos: ChatEntrada) -> ChatSalida:
        """Responde al último mensaje; las acciones con efectos quedan como propuestas."""
        if datos.mensajes[-1].rol != "user":
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, "El último mensaje debe ser del usuario"
            )
        conversacion = [Mensaje(rol=Rol(m.rol), contenido=m.contenido) for m in datos.mensajes]
        try:
            respuesta = agente.conversar(conversacion)
        except ErrorLLM as error:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error)) from error
        return ChatSalida(
            respuesta=respuesta.texto,
            ejecutadas=[salida(a) for a in respuesta.ejecutadas],
            propuestas=[salida(a) for a in respuesta.propuestas],
        )

    @router.post("/confirm")
    def confirmar(datos: ConfirmarEntrada) -> AccionSalida:
        """Ejecuta (aceptar=true) o cancela una acción propuesta."""
        try:
            return salida(agente.confirmar(datos.accion_id, datos.aceptar))
        except AccionNoPendiente as error:
            raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error

    @router.get("/actions")
    def acciones_recientes(limite: int = 50) -> list[AccionSalida]:
        """Últimas acciones del agente, de la más nueva a la más antigua."""
        return [salida(a) for a in acciones().recientes(limite)]

    @router.get("/tools")
    def listar_herramientas() -> list[HerramientaSalida]:
        """Herramientas que el agente puede usar."""
        return [
            HerramientaSalida(
                nombre=t.nombre,
                descripcion=t.descripcion,
                requiere_confirmacion=t.requiere_confirmacion,
                sensible=t.sensible,
            )
            for t in herramientas()
        ]

    return router
