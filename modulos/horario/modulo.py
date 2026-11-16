"""Ficha del modulo horario para el nucleo."""

from nucleo.contrato import Modulo


class Horario(Modulo):
    nombre = "horario"
    titulo = "Horario"
    icono = "🗓️"

    def pagina(self, jarvis):
        from modulos.horario import pagina
        pagina.dibujar(jarvis, self)


def crear(carpeta):
    return Horario(carpeta)
