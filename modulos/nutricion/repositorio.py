"""Acceso a nutricion.db."""

from nucleo.db import conectar
from nucleo import metricas

TABLA = "nutricion"


def guardar(user_id, fecha, kcal, proteina_g, carbohidratos_g, grasas_g, sobrescribir):
    conexion = conectar("nutricion")
    try:
        metricas.guardar_diaria(conexion, TABLA, user_id, fecha, {"kcal": kcal, "proteina_g": proteina_g, "carbohidratos_g": carbohidratos_g, "grasas_g": grasas_g}, sobrescribir)
    finally:
        conexion.close()


def del_dia(user_id, fecha):
    conexion = conectar("nutricion")
    try:
        return metricas.leer_dia(conexion, TABLA, user_id, fecha)
    finally:
        conexion.close()


def historial(user_id):
    conexion = conectar("nutricion")
    try:
        return metricas.historial(conexion, TABLA, user_id)
    finally:
        conexion.close()


def borrar(user_id, fecha):
    conexion = conectar("nutricion")
    try:
        metricas.borrar_dia(conexion, TABLA, user_id, fecha)
    finally:
        conexion.close()
