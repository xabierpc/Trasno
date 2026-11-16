"""Acceso a pasos.db."""

from nucleo.db import conectar
from nucleo import metricas

TABLA = "pasos"


def guardar(user_id, fecha, pasos, sobrescribir):
    conexion = conectar("pasos")
    try:
        metricas.guardar_diaria(conexion, TABLA, user_id, fecha, {"pasos": pasos}, sobrescribir)
    finally:
        conexion.close()


def del_dia(user_id, fecha):
    conexion = conectar("pasos")
    try:
        return metricas.leer_dia(conexion, TABLA, user_id, fecha)
    finally:
        conexion.close()


def historial(user_id):
    conexion = conectar("pasos")
    try:
        return metricas.historial(conexion, TABLA, user_id)
    finally:
        conexion.close()


def borrar(user_id, fecha):
    conexion = conectar("pasos")
    try:
        metricas.borrar_dia(conexion, TABLA, user_id, fecha)
    finally:
        conexion.close()
