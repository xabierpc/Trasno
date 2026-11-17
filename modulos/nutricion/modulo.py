"""Ficha del modulo nutricion para el nucleo."""

from nucleo.contrato import Modulo


class Nutricion(Modulo):
    nombre = "nutricion"
    titulo = "Nutrición"
    icono = ""

    def pagina(self, jarvis):
        from modulos.nutricion import pagina
        pagina.dibujar(jarvis, self)

    def resumen_diario(self, jarvis, fecha):
        from modulos.nutricion import servicio
        fila = servicio.del_dia(jarvis, fecha)
        if fila is None:
            return None
        return str(fila["kcal"]) + " kcal"


def crear(carpeta):
    return Nutricion(carpeta)
