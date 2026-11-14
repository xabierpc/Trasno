"""Herramientas de tracking para el agente: registrar y consultar métricas.

Son funciones pequeñas sobre los casos de uso, con docstrings pensados para el LLM y
respuestas en texto corto. Se registran en `register(ctx)` con `ctx.add_tool`.
"""

from __future__ import annotations

from datetime import date

from pydantic import StrictBool, StrictFloat, StrictInt, StrictStr

from core.contracts import Tool
from modules.tracking.application.casos_uso import CasosUsoTracking

Valor = StrictBool | StrictInt | StrictFloat | StrictStr


def herramientas_tracking(casos: CasosUsoTracking) -> list[Tool]:
    """Las herramientas de tracking sobre `casos`."""

    def metricas() -> str:
        """Lista las métricas que el usuario registra (nombre, tipo y unidad)."""
        lineas = [
            f"- {m.nombre}: {m.tipo.value}"
            + (f" en {m.unidad}" if m.unidad else "")
            + (f" (1-{m.escala_max})" if m.escala_max and not m.unidad else "")
            for m in casos.listar_metricas(solo_activas=True)
        ]
        return "\n".join(lineas) or "No hay métricas."

    def registrar_metrica(nombre: str, valor: Valor, fecha: date) -> str:
        """Guarda el valor de una métrica del día `fecha`: peso en kg, pasos, sueño en minutos,
        ánimo o energía (1-10) o un hábito (true/false). Usa los nombres de `metricas`."""
        entrada = casos.registrar_metrica(nombre, valor, fecha)
        return f"Guardado: {nombre} = {entrada.valor} el {fecha:%d/%m/%Y}."

    def ver_metrica(nombre: str, desde: date, hasta: date) -> str:
        """Valores de una métrica entre dos fechas (incluidas), con su día."""
        entradas = casos.listar_entradas(nombre, desde, hasta)
        lineas = [f"- {e.logical_date:%d/%m/%Y}: {e.valor}" for e in entradas]
        return "\n".join(lineas) or f"No hay valores de {nombre} entre esas fechas."

    return [
        Tool(nombre="metricas", funcion=metricas),
        Tool(nombre="registrar_metrica", funcion=registrar_metrica, sensible=True),
        Tool(nombre="ver_metrica", funcion=ver_metrica, sensible=True),
    ]
