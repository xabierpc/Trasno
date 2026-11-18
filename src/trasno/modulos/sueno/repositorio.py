"""Acceso a sueno.db."""

from trasno.nucleo.db import conectar
from trasno.nucleo import metricas

TABLA = "sueno"


def guardar(user_id, fecha, horas, calidad, sobrescribir):
    conexion = conectar("sueno")
    try:
        metricas.guardar_diaria(conexion, TABLA, user_id, fecha, {"horas": horas, "calidad": calidad}, sobrescribir)
    finally:
        conexion.close()


def del_dia(user_id, fecha):
    conexion = conectar("sueno")
    try:
        return metricas.leer_dia(conexion, TABLA, user_id, fecha)
    finally:
        conexion.close()


def historial(user_id):
    conexion = conectar("sueno")
    try:
        return metricas.historial(conexion, TABLA, user_id)
    finally:
        conexion.close()


def borrar(user_id, fecha):
    conexion = conectar("sueno")
    try:
        metricas.borrar_dia(conexion, TABLA, user_id, fecha)
    finally:
        conexion.close()
