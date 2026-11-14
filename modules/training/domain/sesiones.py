"""Entidades de training: sesión → ejercicios → series, con sus cálculos básicos.

Lo derivado (1RM estimado, volumen) son propiedades: se calcula al pedirlo y nunca se guarda.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime

from modules.training.domain.errores import EjercicioInvalido, SerieInvalida, SesionInvalida

RPE_MIN, RPE_MAX = 1, 10
ENERGIA_MIN, ENERGIA_MAX = 1, 10
_REPS_EPLEY = 30


def _nuevo_id() -> str:
    return str(uuid.uuid4())


def _es_entero(valor: object) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool)


def _es_numero(valor: object) -> bool:
    return isinstance(valor, int | float) and not isinstance(valor, bool) and math.isfinite(valor)


def normalizar_nombre(nombre: str) -> str:
    """Forma única del nombre de un ejercicio: minúsculas y un solo espacio entre palabras."""
    return " ".join(nombre.split()).lower()


def un_rm_epley(peso: float, reps: int) -> float:
    """1RM estimado con la fórmula de Epley: peso · (1 + reps/30); con 1 rep es el propio peso."""
    if reps == 1:
        return float(peso)
    return peso * (1 + reps / _REPS_EPLEY)


@dataclass(frozen=True, kw_only=True)
class Serie:
    """Una serie de un ejercicio: repeticiones, peso en kg y esfuerzo percibido opcional."""

    reps: int
    peso: float
    rpe: float | None = None

    def __post_init__(self) -> None:
        if not _es_entero(self.reps) or self.reps <= 0:
            raise SerieInvalida(f"Las repeticiones deben ser un entero mayor que 0: {self.reps!r}")
        if not _es_numero(self.peso) or self.peso < 0:
            raise SerieInvalida(f"El peso debe ser un número >= 0: {self.peso!r}")
        if self.rpe is not None and not (_es_numero(self.rpe) and RPE_MIN <= self.rpe <= RPE_MAX):
            raise SerieInvalida(f"El RPE debe estar entre {RPE_MIN} y {RPE_MAX}: {self.rpe!r}")

    @property
    def volumen(self) -> float:
        """Kilos movidos en la serie: reps · peso."""
        return self.reps * self.peso

    @property
    def un_rm(self) -> float:
        """1RM estimado (Epley) a partir de esta serie."""
        return un_rm_epley(self.peso, self.reps)


@dataclass(frozen=True, kw_only=True)
class Ejercicio:
    """Un ejercicio dentro de una sesión, con sus series en orden."""

    nombre: str
    series: tuple[Serie, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "nombre", normalizar_nombre(self.nombre))
        object.__setattr__(self, "series", tuple(self.series))
        if not self.nombre:
            raise EjercicioInvalido("El nombre del ejercicio no puede estar vacío")
        if not self.series:
            raise EjercicioInvalido(f"El ejercicio {self.nombre!r} necesita al menos una serie")

    @property
    def volumen(self) -> float:
        return sum(serie.volumen for serie in self.series)

    @property
    def un_rm(self) -> float:
        """Mejor 1RM estimado entre sus series."""
        return max(serie.un_rm for serie in self.series)

    @property
    def peso_maximo(self) -> float:
        return max(serie.peso for serie in self.series)


@dataclass(frozen=True, kw_only=True)
class Sesion:
    """Un entreno de un día lógico. Sin ejercicios es válida (p. ej. salir a correr)."""

    logical_date: date
    tipo: str
    timestamp: datetime
    ejercicios: tuple[Ejercicio, ...] = ()
    duracion_min: int | None = None
    energia_previa: int | None = None
    id: str = field(default_factory=_nuevo_id)

    def __post_init__(self) -> None:
        object.__setattr__(self, "tipo", " ".join(self.tipo.split()).lower())
        object.__setattr__(self, "ejercicios", tuple(self.ejercicios))
        if not self.tipo:
            raise SesionInvalida("El tipo de sesión no puede estar vacío")
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise SesionInvalida("El timestamp debe llevar zona horaria")
        if self.duracion_min is not None and (
            not _es_entero(self.duracion_min) or self.duracion_min <= 0
        ):
            raise SesionInvalida(f"La duración debe ser > 0 minutos: {self.duracion_min!r}")
        if self.energia_previa is not None and not (
            _es_entero(self.energia_previa) and ENERGIA_MIN <= self.energia_previa <= ENERGIA_MAX
        ):
            raise SesionInvalida(
                f"La energía previa debe estar entre {ENERGIA_MIN} y {ENERGIA_MAX}: "
                f"{self.energia_previa!r}"
            )

    @property
    def volumen(self) -> float:
        """Kilos movidos en toda la sesión."""
        return sum(ejercicio.volumen for ejercicio in self.ejercicios)

    def de(self, nombre: str) -> list[Ejercicio]:
        """Apariciones del ejercicio `nombre` en la sesión (puede repetirse)."""
        buscado = normalizar_nombre(nombre)
        return [e for e in self.ejercicios if e.nombre == buscado]
