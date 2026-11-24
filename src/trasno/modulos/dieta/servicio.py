"""Reglas de negocio de dieta: lista semanal de alimentos permitidos y prohibidos.

La semana se identifica por su lunes ('YYYY-MM-DD').
"""

from trasno.modulos.dieta import repositorio
from trasno.nucleo.fechas import a_fecha, lunes_de


def lunes_de_texto(fecha):
    """'YYYY-MM-DD' (cualquier dia) -> lunes de esa semana 'YYYY-MM-DD'."""
    return lunes_de(a_fecha(fecha)).isoformat()


def anadir(jarvis, lunes, nombre, permitido):
    nombre = (nombre or "").strip()
    if nombre == "":
        raise ValueError("Escribe un alimento")
    repositorio.guardar(jarvis.user_id, lunes, nombre, 1 if permitido else 0)


def borrar(jarvis, alimento_id):
    repositorio.borrar(jarvis.user_id, alimento_id)


def semana(jarvis, lunes):
    """dict con 'si' y 'no': filas de alimentos de esa semana."""
    filas = repositorio.de_semana(jarvis.user_id, lunes)
    return {
        "si": [f for f in filas if f["permitido"] == 1],
        "no": [f for f in filas if f["permitido"] == 0],
    }


def semana_anterior_con_datos(jarvis, lunes):
    return repositorio.ultima_semana_antes(jarvis.user_id, lunes)


def copiar_de(jarvis, desde, hasta):
    repositorio.copiar_semana(jarvis.user_id, desde, hasta)


def resumen(jarvis, fecha):
    datos = semana(jarvis, lunes_de_texto(fecha))
    if len(datos["si"]) == 0 and len(datos["no"]) == 0:
        return None
    return str(len(datos["si"])) + " permitidos, " + str(len(datos["no"])) + " a evitar"
