"""Reglas de negocio de pasos."""

from modulos.pasos import repositorio


def registrar(jarvis, fecha, pasos):
    if pasos < 0:
        raise ValueError("Los pasos no pueden ser negativos")
    repositorio.guardar(jarvis.user_id, fecha, pasos, jarvis.sobrescribir_metricas())


def del_dia(jarvis, fecha):
    return repositorio.del_dia(jarvis.user_id, fecha)


def historial(jarvis):
    return repositorio.historial(jarvis.user_id)


def borrar(jarvis, fecha):
    repositorio.borrar(jarvis.user_id, fecha)
