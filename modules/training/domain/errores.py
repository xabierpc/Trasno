"""Errores de dominio de training."""

from __future__ import annotations


class ErrorTraining(Exception):
    """Base de los errores de training."""


class SerieInvalida(ErrorTraining):
    """Una serie no cumple las reglas (reps > 0, peso >= 0, RPE entre 1 y 10)."""


class EjercicioInvalido(ErrorTraining):
    """Un ejercicio no tiene nombre o no tiene series."""


class SesionInvalida(ErrorTraining):
    """Una sesión es incoherente (tipo vacío, duración o energía fuera de rango...)."""


class SesionNoEncontrada(ErrorTraining):
    """No existe ninguna sesión con ese identificador."""

    def __init__(self, sesion_id: str) -> None:
        super().__init__(f"No existe la sesión {sesion_id!r}")
        self.sesion_id = sesion_id


class EjercicioNoEncontrado(ErrorTraining):
    """No hay ninguna sesión registrada con ese ejercicio."""

    def __init__(self, nombre: str) -> None:
        super().__init__(f"No hay sesiones con el ejercicio {nombre!r}")
        self.nombre = nombre


class SerieTemporalNoEncontrada(ErrorTraining):
    """El proveedor de series de training no ofrece esa serie."""

    def __init__(self, nombre: str) -> None:
        super().__init__(f"Training no ofrece la serie {nombre!r}")
        self.nombre = nombre
