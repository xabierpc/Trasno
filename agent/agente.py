"""El agente: conversación con el LLM y bucle de herramientas, con confirmación y log.

Un turno: el LLM recibe la conversación y las herramientas; si pide herramientas, se ejecutan
(o se dejan propuestas, si requieren confirmación) y se le devuelven los resultados, hasta que
responde con texto. Todo lo que se ejecuta o se propone queda en `ctx.acciones`.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import ValidationError
from pydantic_core import to_jsonable_python

from agent.esquemas import argumentos, esquema_openai
from agent.mensajes import LLM, LlamadaHerramienta, Mensaje, Rol
from agent.prompt import instrucciones
from core.contracts import Accion, EstadoAccion, RegistroAcciones, Tool

logger = logging.getLogger(__name__)

MAX_PASOS = 8  # llamadas al LLM por turno, para no entrar en bucle
MAX_RESULTADO = 2000  # caracteres del resultado de una herramienta que se le devuelven


class AccionNoPendiente(Exception):
    """Se intenta confirmar algo que no existe o que ya no está pendiente."""


@dataclass(frozen=True)
class RespuestaAgente:
    """Lo que el agente contesta en un turno."""

    texto: str
    ejecutadas: list[Accion] = field(default_factory=list)
    propuestas: list[Accion] = field(default_factory=list)


def _ahora() -> datetime:
    return datetime.now(UTC)


class Agente:
    """Conversa con un LLM y le deja usar las herramientas que han registrado los módulos."""

    def __init__(
        self,
        llm: LLM,
        herramientas: Callable[[], Sequence[Tool]],
        acciones: Callable[[], RegistroAcciones],
        zona: str,
        ventana_madrugada: tuple[time, time],
        reloj: Callable[[], datetime] = _ahora,
    ) -> None:
        self._llm = llm
        self._herramientas = herramientas
        self._acciones = acciones
        self._zona = ZoneInfo(zona)
        self._ventana = ventana_madrugada
        self._reloj = reloj

    def conversar(self, conversacion: Sequence[Mensaje]) -> RespuestaAgente:
        """Responde al último mensaje del usuario. `conversacion` no incluye el de sistema."""
        herramientas = {t.nombre: t for t in self._herramientas()}
        esquemas = [esquema_openai(t) for t in herramientas.values()]
        ahora = self._reloj().astimezone(self._zona)
        mensajes = [
            Mensaje(rol=Rol.SISTEMA, contenido=instrucciones(ahora, self._ventana)),
            *conversacion,
        ]
        ejecutadas: list[Accion] = []
        propuestas: list[Accion] = []
        for _ in range(MAX_PASOS):
            respuesta = self._llm.responder(mensajes, esquemas)
            if not respuesta.llamadas:
                return RespuestaAgente(respuesta.texto, ejecutadas, propuestas)
            mensajes.append(
                Mensaje(
                    rol=Rol.ASISTENTE,
                    contenido=respuesta.texto,
                    llamadas=tuple(respuesta.llamadas),
                )
            )
            for llamada in respuesta.llamadas:
                contenido, accion = self._atender(llamada, herramientas)
                if accion is not None:
                    destino = propuestas if accion.estado is EstadoAccion.PROPUESTA else ejecutadas
                    destino.append(accion)
                mensajes.append(
                    Mensaje(rol=Rol.HERRAMIENTA, contenido=contenido, llamada_id=llamada.id)
                )
        logger.warning("El agente ha llegado al límite de %d pasos", MAX_PASOS)
        return RespuestaAgente(
            "No he conseguido terminar: ¿puedes pedírmelo de otra forma?", ejecutadas, propuestas
        )

    def confirmar(self, accion_id: int, aceptar: bool) -> Accion:
        """Ejecuta (o cancela) una acción que el agente dejó propuesta."""
        registro = self._acciones()
        accion = registro.obtener(accion_id)
        if accion is None or accion.estado is not EstadoAccion.PROPUESTA:
            raise AccionNoPendiente(f"No hay ninguna acción pendiente con id {accion_id}")
        if not aceptar:
            return registro.cambiar_estado(accion_id, EstadoAccion.CANCELADA, "Cancelada")
        tool = {t.nombre: t for t in self._herramientas()}.get(accion.herramienta)
        if tool is None:
            return registro.cambiar_estado(
                accion_id, EstadoAccion.FALLIDA, "La herramienta ya no existe"
            )
        try:
            resultado = _texto(tool.funcion(**argumentos(tool, accion.argumentos)))
        except Exception as error:
            logger.info("La acción %s ha fallado al confirmarla", accion_id, exc_info=True)
            return registro.cambiar_estado(accion_id, EstadoAccion.FALLIDA, f"Error: {error}")
        return registro.cambiar_estado(accion_id, EstadoAccion.EJECUTADA, resultado)

    def _atender(
        self, llamada: LlamadaHerramienta, herramientas: dict[str, Tool]
    ) -> tuple[str, Accion | None]:
        """Ejecuta o propone la llamada. Devuelve lo que se le dice al LLM y la acción guardada."""
        tool = herramientas.get(llamada.nombre)
        if tool is None:
            return f"Error: no existe la herramienta {llamada.nombre!r}.", None
        try:
            kwargs = argumentos(tool, llamada.argumentos)
        except ValidationError as error:
            return (
                f"Error en los argumentos: {_errores(error)}. Corrígelos y vuelve a llamarla.",
                None,
            )

        registro = self._acciones()
        ahora = self._reloj()
        if tool.requiere_confirmacion:
            accion = registro.guardar(
                Accion(
                    herramienta=tool.nombre,
                    argumentos=to_jsonable_python(llamada.argumentos),
                    estado=EstadoAccion.PROPUESTA,
                    timestamp=ahora,
                )
            )
            return (
                f"Pendiente de confirmación (propuesta {accion.id}): no se ha ejecutado todavía. "
                "El usuario la verá con un botón para confirmarla.",
                accion,
            )
        try:
            resultado = _texto(tool.funcion(**kwargs))
            estado = EstadoAccion.EJECUTADA
        except Exception as error:
            logger.info("La herramienta %s ha fallado", tool.nombre, exc_info=True)
            resultado, estado = f"Error: {error}", EstadoAccion.FALLIDA
        accion = registro.guardar(
            Accion(
                herramienta=tool.nombre,
                argumentos=to_jsonable_python(llamada.argumentos),
                estado=estado,
                resultado=resultado,
                timestamp=ahora,
            )
        )
        return resultado[:MAX_RESULTADO], accion


def _texto(resultado: Any) -> str:
    if isinstance(resultado, str):
        return resultado
    if resultado is None:
        return "Hecho."
    return json.dumps(to_jsonable_python(resultado), ensure_ascii=False)


def _errores(error: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(str(p) for p in e['loc']) or 'argumentos'}: {e['msg']}" for e in error.errors()
    )
