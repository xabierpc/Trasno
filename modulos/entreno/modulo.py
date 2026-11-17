"""Ficha del modulo entreno para el nucleo."""

from nucleo.contrato import Modulo


class Entreno(Modulo):
    nombre = "entreno"
    titulo = "Entreno"
    icono = ""
    version_esquema = 2     # v2: tabla pr_manual

    def pagina(self, jarvis):
        from modulos.entreno import pagina
        pagina.dibujar(jarvis, self)

    def resumen_diario(self, jarvis, fecha):
        from modulos.entreno import servicio
        return servicio.resumen(jarvis, fecha)


def crear(carpeta):
    return Entreno(carpeta)
