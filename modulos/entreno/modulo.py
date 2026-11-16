"""Ficha del modulo entreno para el nucleo."""

from nucleo.contrato import Modulo


class Entreno(Modulo):
    nombre = "entreno"
    titulo = "Entreno"
    icono = "🏋️"

    def pagina(self, jarvis):
        from modulos.entreno import pagina
        pagina.dibujar(jarvis, self)


def crear(carpeta):
    return Entreno(carpeta)
