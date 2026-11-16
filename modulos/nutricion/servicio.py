"""Reglas de negocio de nutricion."""

from modulos.nutricion import repositorio


def registrar(jarvis, fecha, kcal, proteina_g, carbohidratos_g, grasas_g):
    for valor in (kcal, proteina_g, carbohidratos_g, grasas_g):
        if valor < 0:
            raise ValueError("Ningún valor puede ser negativo")
    repositorio.guardar(jarvis.user_id, fecha, kcal, proteina_g, carbohidratos_g, grasas_g, jarvis.sobrescribir_metricas())


def del_dia(jarvis, fecha):
    return repositorio.del_dia(jarvis.user_id, fecha)


def historial(jarvis):
    return repositorio.historial(jarvis.user_id)


def borrar(jarvis, fecha):
    repositorio.borrar(jarvis.user_id, fecha)
