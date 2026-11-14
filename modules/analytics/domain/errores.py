"""Errores de dominio de analytics."""

from __future__ import annotations


class ErrorAnalytics(Exception):
    """Base de los errores de analytics."""


class SerieNoEncontrada(ErrorAnalytics):
    """Ningún proveedor ofrece una serie con ese nombre."""

    def __init__(self, nombre: str) -> None:
        super().__init__(f"No hay ninguna serie llamada {nombre!r}")
        self.nombre = nombre


class SerieDuplicada(ErrorAnalytics):
    """Más de un proveedor ofrece una serie con el mismo nombre."""

    def __init__(self, nombre: str) -> None:
        super().__init__(f"La serie {nombre!r} la ofrece más de un proveedor")
        self.nombre = nombre
