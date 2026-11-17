"""Ficha del modulo asistente para el nucleo."""

from nucleo.contrato import Modulo


class Asistente(Modulo):
    nombre = "asistente"
    titulo = "Asistente"
    icono = ""
    # Los recordatorios enlazados a tareas solo si jarvis.obtener("agenda") no es None.

    def pagina(self, jarvis):
        from modulos.asistente import pagina
        pagina.dibujar(jarvis, self)


def crear(carpeta):
    return Asistente(carpeta)
