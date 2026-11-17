"""Ficha del modulo agenda para el nucleo."""

from nucleo.contrato import Modulo


class Agenda(Modulo):
    nombre = "agenda"
    titulo = "Agenda"
    icono = ""
    version_esquema = 2     # v2: tabla dia_importante
    # Usa el horario si existe: jarvis.obtener("horario") devuelve None si no.

    def pagina(self, jarvis):
        from modulos.agenda import pagina
        pagina.dibujar(jarvis, self)

    def resumen_diario(self, jarvis, fecha):
        from modulos.agenda import servicio
        return servicio.resumen(jarvis, fecha)


def crear(carpeta):
    return Agenda(carpeta)
