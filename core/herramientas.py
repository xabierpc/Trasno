"""Validación de las herramientas que los módulos ofrecen al agente (`ctx.add_tool`).

Se comprueba al registrar, no cuando el LLM las llama: un error aquí sale al arrancar la API.
"""

from __future__ import annotations

import inspect
import re
import typing
from dataclasses import replace

from core.contracts import Tool

_NOMBRE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


class HerramientaInvalida(ValueError):
    """La herramienta no cumple la regla 11 (tipos y docstring) o su nombre no vale."""


def validar(tool: Tool) -> Tool:
    """Devuelve la herramienta lista para el agente (con descripción) o lanza el motivo."""
    if not _NOMBRE.match(tool.nombre):
        raise HerramientaInvalida(
            f"Nombre de herramienta no válido: {tool.nombre!r} (minúsculas, números y _)"
        )
    if not callable(tool.funcion):
        raise HerramientaInvalida(f"La herramienta {tool.nombre!r} no es llamable")

    docstring = inspect.getdoc(tool.funcion) or ""
    descripcion = tool.descripcion.strip() or docstring.strip().split("\n")[0]
    if not descripcion:
        raise HerramientaInvalida(f"La herramienta {tool.nombre!r} no tiene docstring")

    try:
        tipos = typing.get_type_hints(tool.funcion)
    except (NameError, TypeError) as error:
        raise HerramientaInvalida(
            f"No se pueden leer los tipos de {tool.nombre!r}: {error}"
        ) from error
    sin_tipo = [
        nombre
        for nombre, parametro in inspect.signature(tool.funcion).parameters.items()
        if nombre not in tipos
        and parametro.kind not in (parametro.VAR_POSITIONAL, parametro.VAR_KEYWORD)
    ]
    if sin_tipo:
        raise HerramientaInvalida(
            f"La herramienta {tool.nombre!r} tiene parámetros sin tipo: {', '.join(sin_tipo)}"
        )
    return replace(tool, descripcion=descripcion)
