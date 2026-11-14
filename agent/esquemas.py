"""Herramienta ↔ LLM: esquema JSON de los parámetros y validación de los argumentos.

El esquema se saca de la firma de la función (tipos y valores por defecto) con Pydantic, así
el LLM ve exactamente lo que la función acepta, y los argumentos que mande se convierten a esos
tipos (p. ej. "2026-11-15" → date) antes de llamarla.
"""

from __future__ import annotations

import inspect
import typing
from functools import cache
from typing import Any

from pydantic import BaseModel, ConfigDict, create_model

from core.contracts import Tool


@cache
def _modelo(funcion: Any, nombre: str) -> type[BaseModel]:
    tipos = typing.get_type_hints(funcion, include_extras=True)
    campos: dict[str, Any] = {}
    for parametro in inspect.signature(funcion).parameters.values():
        if parametro.kind in (parametro.VAR_POSITIONAL, parametro.VAR_KEYWORD):
            continue
        defecto = ... if parametro.default is parametro.empty else parametro.default
        campos[parametro.name] = (tipos[parametro.name], defecto)
    return create_model(  # type: ignore[call-overload,no-any-return]
        f"Argumentos_{nombre}", __config__=ConfigDict(extra="forbid"), **campos
    )


def modelo_de(tool: Tool) -> type[BaseModel]:
    """Modelo Pydantic con los parámetros de la herramienta."""
    return _modelo(tool.funcion, tool.nombre)


def esquema_openai(tool: Tool) -> dict[str, Any]:
    """La herramienta en el formato `tools` de la API de OpenAI."""
    esquema = _sin_referencias(modelo_de(tool).model_json_schema())
    return {
        "type": "function",
        "function": {"name": tool.nombre, "description": tool.descripcion, "parameters": esquema},
    }


def argumentos(tool: Tool, datos: dict[str, Any]) -> dict[str, Any]:
    """Valida y convierte los argumentos del LLM. Lanza `pydantic.ValidationError` si no valen."""
    modelo = modelo_de(tool).model_validate(datos)
    # dict(modelo) y no model_dump(): conserva los objetos (date, enums, dataclasses) tal cual.
    return dict(modelo)


def _sin_referencias(esquema: dict[str, Any]) -> dict[str, Any]:
    """Sustituye los `$ref` por su definición: no todos los modelos locales entienden `$defs`."""
    definiciones = esquema.pop("$defs", {})
    for definicion in definiciones.values():
        # El docstring de la clase (p. ej. de un enum) es para programadores, no para el LLM.
        definicion.pop("description", None)

    def resolver(nodo: Any) -> Any:
        if isinstance(nodo, dict):
            if "$ref" in nodo:
                return resolver(definiciones[nodo["$ref"].rsplit("/", 1)[-1]])
            # "title" con texto es el nombre que pone Pydantic; un parámetro "title" sería un dict.
            return {
                k: resolver(v) for k, v in nodo.items() if not (k == "title" and isinstance(v, str))
            }
        if isinstance(nodo, list):
            return [resolver(v) for v in nodo]
        return nodo

    return resolver(esquema)  # type: ignore[no-any-return]
