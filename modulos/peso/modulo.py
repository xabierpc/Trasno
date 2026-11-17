"""Ficha del modulo peso para el nucleo."""

from nucleo.contrato import Modulo


class Peso(Modulo):
    nombre = "peso"
    titulo = "Peso"
    icono = ""

    def pagina(self, jarvis):
        from modulos.peso import pagina
        pagina.dibujar(jarvis, self)

    def resumen_diario(self, jarvis, fecha):
        from modulos.peso import servicio
        fila = servicio.del_dia(jarvis, fecha)
        if fila is None:
            return None
        return str(fila["kg"]) + " kg"


def crear(carpeta):
    return Peso(carpeta)
