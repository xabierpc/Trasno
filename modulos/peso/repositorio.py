"""Acceso a peso.db."""

from nucleo.db import conectar
from nucleo import metricas

TABLA = "peso"


def guardar(user_id, fecha, kg, sobrescribir):
    conexion = conectar("peso")
    try:
        metricas.guardar_diaria(conexion, TABLA, user_id, fecha, {"kg": kg}, sobrescribir)
    finally:
        conexion.close()


def del_dia(user_id, fecha):
    conexion = conectar("peso")
    try:
        return metricas.leer_dia(conexion, TABLA, user_id, fecha)
    finally:
        conexion.close()


def historial(user_id):
    conexion = conectar("peso")
    try:
        return metricas.historial(conexion, TABLA, user_id)
    finally:
        conexion.close()


def borrar(user_id, fecha):
    conexion = conectar("peso")
    try:
        metricas.borrar_dia(conexion, TABLA, user_id, fecha)
    finally:
        conexion.close()
