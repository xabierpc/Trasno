"""Tipos de la conversación con el LLM y el port `LLM` que implementan los adaptadores."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol


class Rol(StrEnum):
    """Quién habla. Los valores son los de la API de OpenAI."""

    SISTEMA = "system"
    USUARIO = "user"
    ASISTENTE = "assistant"
    HERRAMIENTA = "tool"


@dataclass(frozen=True)
class LlamadaHerramienta:
    """El LLM pide ejecutar la herramienta `nombre` con `argumentos`."""

    id: str
    nombre: str
    argumentos: dict[str, Any]


@dataclass(frozen=True, kw_only=True)
class Mensaje:
    """Un mensaje de la conversación.

    Un mensaje del asistente puede traer `llamadas`; la respuesta a cada llamada es un mensaje
    con rol HERRAMIENTA y el `llamada_id` de la llamada a la que responde.
    """

    rol: Rol
    contenido: str = ""
    llamadas: tuple[LlamadaHerramienta, ...] = ()
    llamada_id: str | None = None


@dataclass(frozen=True)
class RespuestaLLM:
    """Lo que devuelve el LLM en un paso: texto, llamadas a herramientas o las dos cosas."""

    texto: str = ""
    llamadas: list[LlamadaHerramienta] = field(default_factory=list)


class ErrorLLM(Exception):
    """El LLM no responde o devuelve algo que no se entiende."""


class LLM(Protocol):
    """Un modelo de lenguaje con uso de herramientas (tool calling)."""

    def responder(
        self, mensajes: list[Mensaje], herramientas: list[dict[str, Any]]
    ) -> RespuestaLLM:
        """Siguiente paso de la conversación. `herramientas` va en el formato de OpenAI."""
        ...
