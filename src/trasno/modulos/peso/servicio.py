"""Reglas de negocio de peso."""

from trasno.modulos.peso import repositorio


def registrar(jarvis, fecha, kg):
    if kg <= 0:
        raise ValueError("El peso tiene que ser mayor que 0")
    repositorio.guardar(jarvis.user_id, fecha, kg, jarvis.sobrescribir_metricas())


def del_dia(jarvis, fecha):
    return repositorio.del_dia(jarvis.user_id, fecha)


def historial(jarvis):
    return repositorio.historial(jarvis.user_id)


def borrar(jarvis, fecha):
    repositorio.borrar(jarvis.user_id, fecha)
