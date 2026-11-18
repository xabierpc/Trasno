"""Reglas de negocio de sueno."""

from trasno.modulos.sueno import repositorio


def registrar(jarvis, fecha, horas, calidad):
    if horas < 0 or horas > 24:
        raise ValueError("Las horas tienen que estar entre 0 y 24")
    if calidad < 1 or calidad > 5:
        raise ValueError("La calidad va de 1 a 5")
    repositorio.guardar(jarvis.user_id, fecha, horas, calidad, jarvis.sobrescribir_metricas())


def del_dia(jarvis, fecha):
    return repositorio.del_dia(jarvis.user_id, fecha)


def historial(jarvis):
    return repositorio.historial(jarvis.user_id)


def borrar(jarvis, fecha):
    repositorio.borrar(jarvis.user_id, fecha)
