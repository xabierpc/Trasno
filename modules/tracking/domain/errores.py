"""Errores de dominio de tracking."""

from __future__ import annotations


class ErrorTracking(Exception):
    """Base de los errores de tracking."""


class DefinicionInvalida(ErrorTracking):
    """La configuración de una métrica es incoherente (p. ej. escala sin N)."""


class EntradaInvalida(ErrorTracking):
    """Una entrada no cumple las reglas comunes (timestamp sin zona, slot negativo)."""


class ValorInvalido(ErrorTracking):
    """Base de los errores de un valor que no encaja con su métrica."""

    def __init__(self, metrica: str, valor: object, motivo: str) -> None:
        super().__init__(f"Valor {valor!r} no válido para {metrica!r}: {motivo}")
        self.metrica = metrica
        self.valor = valor


class TipoIncorrecto(ValorInvalido):
    """El valor no es del tipo Python que exige la métrica."""


class ValorFueraDeRango(ValorInvalido):
    """El valor es del tipo correcto pero está fuera de los límites permitidos."""


class CategoriaDesconocida(ValorInvalido):
    """La categoría no está entre las definidas para la métrica."""


class MetricaNoEncontrada(ErrorTracking):
    """No existe ninguna métrica con ese nombre."""

    def __init__(self, nombre: str) -> None:
        super().__init__(f"No existe la métrica {nombre!r}")
        self.nombre = nombre


class MetricaDuplicada(ErrorTracking):
    """Ya existe una métrica con ese nombre."""

    def __init__(self, nombre: str) -> None:
        super().__init__(f"Ya existe la métrica {nombre!r}")
        self.nombre = nombre


class EntradaNoEncontrada(ErrorTracking):
    """No existe ninguna entrada con ese identificador."""

    def __init__(self, entrada_id: str) -> None:
        super().__init__(f"No existe la entrada {entrada_id!r}")
        self.entrada_id = entrada_id
