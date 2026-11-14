"""Herramientas de training para el agente: registrar y consultar entrenos."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from core.contracts import Tool
from modules.training.application.casos_uso import CasosUsoTraining
from modules.training.domain.sesiones import Ejercicio, Serie


@dataclass
class EjercicioSimple:
    """Un ejercicio como lo dice el usuario: «press banca 3x8 con 60 kg»."""

    nombre: str
    series: int
    reps: int
    peso: float = 0.0  # 0 = peso corporal


def herramientas_training(casos: CasosUsoTraining) -> list[Tool]:
    """Las herramientas de training sobre `casos`."""

    def registrar_entreno(
        fecha: date,
        tipo: str,
        ejercicios: list[EjercicioSimple] | None = None,
        duracion_min: int | None = None,
    ) -> str:
        """Guarda un entreno del día `fecha`: tipo (fuerza, correr…), ejercicios con series,
        repeticiones y peso, y duración en minutos. Dice si se ha batido algún récord."""
        guardada = casos.registrar_sesion(
            fecha,
            tipo,
            [
                Ejercicio(nombre=e.nombre, series=(Serie(reps=e.reps, peso=e.peso),) * e.series)
                for e in ejercicios or []
            ],
            duracion_min=duracion_min,
        )
        texto = f"Entreno de {guardada.sesion.tipo} guardado ({guardada.sesion.volumen:g} kg)."
        for r in guardada.records:
            texto += (
                f" Récord de {r.tipo.value} en {r.ejercicio}: {r.valor:g} (antes {r.anterior:g})."
            )
        return texto

    def entrenos(desde: date, hasta: date) -> str:
        """Entrenos entre dos fechas (incluidas) con sus ejercicios."""
        lineas = []
        for s in casos.listar_sesiones(desde, hasta):
            detalle = ", ".join(
                f"{e.nombre} {len(e.series)}x{e.series[0].reps}x{e.series[0].peso:g}"
                for e in s.ejercicios
            )
            lineas.append(
                f"- {s.logical_date:%d/%m/%Y} {s.tipo}" + (f": {detalle}" if detalle else "")
            )
        return "\n".join(lineas) or "No hay entrenos entre esas fechas."

    return [
        Tool(nombre="registrar_entreno", funcion=registrar_entreno),
        Tool(nombre="entrenos", funcion=entrenos),
    ]
