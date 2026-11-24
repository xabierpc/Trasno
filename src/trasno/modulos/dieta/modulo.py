"""Ficha del modulo dieta para el nucleo."""

from trasno.nucleo.contrato import Modulo


class Dieta(Modulo):
    nombre = "dieta"
    titulo = "Dieta semanal"
    icono = ""
    orden_inicio = 30

    def pagina(self, jarvis):
        from trasno.modulos.dieta import pagina
        pagina.dibujar(jarvis, self)

    def inicio(self, jarvis, fecha):
        from trasno.modulos.dieta import pagina
        pagina.bloque_inicio(jarvis, fecha)

    def resumen_diario(self, jarvis, fecha):
        from trasno.modulos.dieta import servicio
        return servicio.resumen(jarvis, fecha)


def crear(carpeta):
    return Dieta(carpeta)
