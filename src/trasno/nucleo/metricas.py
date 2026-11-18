"""Utilidad comun para las metricas diarias (una fila por usuario y dia).

Los modulos de metricas la usan; los nombres de tabla y columnas los pone
siempre el codigo del modulo, nunca el usuario.
"""


class YaRegistrado(Exception):
    """Ya hay un valor ese dia y la configuracion dice no sobrescribir."""


def guardar_diaria(conexion, tabla, user_id, fecha, valores, sobrescribir):
    existe = conexion.execute(
        "SELECT 1 FROM " + tabla + " WHERE user_id = ? AND fecha = ?",
        (user_id, fecha),
    ).fetchone()

    if existe is not None:
        if not sobrescribir:
            raise YaRegistrado(tabla + " ya tiene un valor el " + fecha)
        asignaciones = ", ".join([columna + " = ?" for columna in valores])
        parametros = list(valores.values()) + [user_id, fecha]
        conexion.execute(
            "UPDATE " + tabla + " SET " + asignaciones + " WHERE user_id = ? AND fecha = ?",
            parametros,
        )
    else:
        columnas = ["user_id", "fecha"] + list(valores)
        huecos = ", ".join(["?"] * len(columnas))
        parametros = [user_id, fecha] + list(valores.values())
        conexion.execute(
            "INSERT INTO " + tabla + " (" + ", ".join(columnas) + ") VALUES (" + huecos + ")",
            parametros,
        )
    conexion.commit()


def leer_dia(conexion, tabla, user_id, fecha):
    return conexion.execute(
        "SELECT * FROM " + tabla + " WHERE user_id = ? AND fecha = ?",
        (user_id, fecha),
    ).fetchone()


def historial(conexion, tabla, user_id):
    return conexion.execute(
        "SELECT * FROM " + tabla + " WHERE user_id = ? ORDER BY fecha",
        (user_id,),
    ).fetchall()


def borrar_dia(conexion, tabla, user_id, fecha):
    conexion.execute("DELETE FROM " + tabla + " WHERE user_id = ? AND fecha = ?", (user_id, fecha))
    conexion.commit()
