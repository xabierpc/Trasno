"""Ficha del modulo horario para el nucleo."""

from nucleo.contrato import Modulo


class Horario(Modulo):
    nombre = "horario"
    titulo = "Horario"
    icono = ""

    def pagina(self, jarvis):
        from modulos.horario import pagina
        pagina.dibujar(jarvis, self)

    def resumen_diario(self, jarvis, fecha):
        from modulos.horario import servicio
        return servicio.resumen(jarvis, fecha)

    # ---------- API para otros modulos (via jarvis.obtener("horario")) ----------
    def bloques_del_dia(self, jarvis, fecha):
        """Lista de dicts con el horario real de fecha ('YYYY-MM-DD'), excepciones aplicadas."""
        from modulos.horario import servicio
        return servicio.bloques_del_dia(jarvis, fecha)


def crear(carpeta):
    return Horario(carpeta)
