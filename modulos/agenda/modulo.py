"""Ficha del modulo agenda para el nucleo."""

from nucleo.contrato import Modulo


class Agenda(Modulo):
    nombre = "agenda"
    titulo = "Agenda"
    icono = "📅"

    def pagina(self, jarvis):
        from modulos.agenda import pagina
        pagina.dibujar(jarvis, self)


def crear(carpeta):
    return Agenda(carpeta)
