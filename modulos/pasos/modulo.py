"""Ficha del modulo pasos para el nucleo."""

from nucleo.contrato import Modulo


class Pasos(Modulo):
    nombre = "pasos"
    titulo = "Pasos"
    icono = "👟"

    def pagina(self, jarvis):
        from modulos.pasos import pagina
        pagina.dibujar(jarvis, self)

    def resumen_diario(self, jarvis, fecha):
        from modulos.pasos import servicio
        fila = servicio.del_dia(jarvis, fecha)
        if fila is None:
            return None
        return str(fila["pasos"]) + " pasos"


def crear(carpeta):
    return Pasos(carpeta)
