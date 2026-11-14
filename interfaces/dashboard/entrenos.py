"""Ayudas de presentación de la página «Entrenos»: de las filas del formulario al cuerpo de la API.

Aquí no hay reglas de negocio: solo se agrupan las filas que el usuario ha rellenado. Validar
repeticiones, pesos o RPE es cosa del dominio de training, que responde con un 422.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FilaEntreno:
    """Una fila del formulario: `series` series iguales de un ejercicio."""

    ejercicio: str | None
    series: int
    reps: int | None
    peso: float | None
    rpe: float | None = None

    @property
    def vacia(self) -> bool:
        return not (self.ejercicio or "").strip() and self.reps is None and self.peso is None


def ejercicios_de_filas(filas: Iterable[FilaEntreno]) -> tuple[list[dict[str, Any]], list[str]]:
    """Convierte las filas en la lista `ejercicios` de POST /training/sessions.

    Devuelve (ejercicios, errores). Las filas vacías se ignoran, las del mismo ejercicio se
    juntan en orden y un peso vacío cuenta como 0 (peso corporal).
    """
    por_nombre: dict[str, dict[str, Any]] = {}
    errores: list[str] = []
    for numero, fila in enumerate(filas, start=1):
        if fila.vacia:
            continue
        nombre = " ".join((fila.ejercicio or "").split())
        if not nombre:
            errores.append(f"Fila {numero}: falta el ejercicio.")
            continue
        if fila.reps is None:
            errores.append(f"Fila {numero}: faltan las repeticiones de {nombre}.")
            continue
        serie = {"reps": fila.reps, "peso": fila.peso or 0.0, "rpe": fila.rpe}
        ejercicio = por_nombre.setdefault(nombre.lower(), {"nombre": nombre, "series": []})
        ejercicio["series"] += [dict(serie) for _ in range(fila.series)]
    return list(por_nombre.values()), errores


def resumen_ejercicio(ejercicio: dict[str, Any]) -> str:
    """Texto corto de un ejercicio: «press banca 3x8x60, 1x6x65»."""
    grupos: list[list[Any]] = []  # [nº de series, reps, peso] de series iguales seguidas
    for serie in ejercicio["series"]:
        if grupos and grupos[-1][1:] == [serie["reps"], serie["peso"]]:
            grupos[-1][0] += 1
        else:
            grupos.append([1, serie["reps"], serie["peso"]])
    partes = ", ".join(f"{n}x{reps}x{peso:g}" for n, reps, peso in grupos)
    return f"{ejercicio['nombre']} {partes}"
