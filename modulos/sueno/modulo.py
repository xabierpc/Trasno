"""Ficha del modulo sueno para el nucleo."""

from nucleo.contrato import Modulo


class Sueno(Modulo):
    nombre = "sueno"
    titulo = "Sueño"
    icono = ""

    def pagina(self, jarvis):
        from modulos.sueno import pagina
        pagina.dibujar(jarvis, self)

    def resumen_diario(self, jarvis, fecha):
        from modulos.sueno import servicio
        fila = servicio.del_dia(jarvis, fecha)
        if fila is None:
            return None
        return str(fila["horas"]) + " h"


def crear(carpeta):
    return Sueno(carpeta)
