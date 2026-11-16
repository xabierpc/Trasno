"""Ficha del modulo productividad para el nucleo."""

from nucleo.contrato import Modulo


class Productividad(Modulo):
    nombre = "productividad"
    titulo = "Horas productivas"
    icono = "⏱️"
    # Usa la agenda si existe: jarvis.obtener("agenda") devuelve None si no.

    def pagina(self, jarvis):
        from modulos.productividad import pagina
        pagina.dibujar(jarvis, self)


def crear(carpeta):
    return Productividad(carpeta)
