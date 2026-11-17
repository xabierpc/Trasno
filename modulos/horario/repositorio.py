"""Acceso a horario.db (SQL). Solo habla con su propia BD."""

from contextlib import contextmanager

from nucleo.db import conectar


@contextmanager
def abrir():
    conexion = conectar("horario")
    try:
        yield conexion
        conexion.commit()
    finally:
        conexion.close()


# ---------- bloques ----------
def crear_bloque(user_id, tipo, titulo, dia_semana, hora_inicio, hora_fin, ubicacion, vigente_desde, vigente_hasta):
    with abrir() as conexion:
        cursor = conexion.execute(
            "INSERT INTO bloque_horario (user_id, tipo, titulo, dia_semana, hora_inicio, hora_fin, "
            "ubicacion, vigente_desde, vigente_hasta) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, tipo, titulo, dia_semana, hora_inicio, hora_fin, ubicacion, vigente_desde, vigente_hasta),
        )
        return cursor.lastrowid


def actualizar_bloque(user_id, bloque_id, valores):
    asignaciones = ", ".join([columna + " = ?" for columna in valores])
    parametros = list(valores.values()) + [user_id, bloque_id]
    with abrir() as conexion:
        conexion.execute("UPDATE bloque_horario SET " + asignaciones + " WHERE user_id = ? AND id = ?", parametros)


def borrar_bloque(user_id, bloque_id):
    with abrir() as conexion:
        conexion.execute("DELETE FROM bloque_horario WHERE user_id = ? AND id = ?", (user_id, bloque_id))


def obtener_bloque(user_id, bloque_id):
    with abrir() as conexion:
        return conexion.execute(
            "SELECT * FROM bloque_horario WHERE user_id = ? AND id = ?", (user_id, bloque_id)
        ).fetchone()


def listar_bloques(user_id):
    with abrir() as conexion:
        return conexion.execute(
            "SELECT * FROM bloque_horario WHERE user_id = ? ORDER BY dia_semana, hora_inicio",
            (user_id,),
        ).fetchall()


def bloques_vigentes(user_id, dia_semana, fecha):
    """Bloques de ese dia de la semana que estan en vigor en fecha."""
    with abrir() as conexion:
        return conexion.execute(
            "SELECT * FROM bloque_horario WHERE user_id = ? AND dia_semana = ? "
            "AND vigente_desde <= ? AND (vigente_hasta IS NULL OR vigente_hasta >= ?) "
            "ORDER BY hora_inicio",
            (user_id, dia_semana, fecha, fecha),
        ).fetchall()


def bloques_mismo_dia(user_id, dia_semana):
    with abrir() as conexion:
        return conexion.execute(
            "SELECT * FROM bloque_horario WHERE user_id = ? AND dia_semana = ?",
            (user_id, dia_semana),
        ).fetchall()


# ---------- excepciones ----------
def guardar_excepcion(user_id, bloque_id, fecha, tipo, hora_inicio, hora_fin, motivo):
    """Una excepcion por bloque y dia: si ya habia una, se sustituye."""
    with abrir() as conexion:
        conexion.execute(
            "INSERT INTO excepcion_horario (user_id, bloque_id, fecha, tipo, hora_inicio, hora_fin, motivo) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT (bloque_id, fecha) DO UPDATE SET tipo = excluded.tipo, "
            "hora_inicio = excluded.hora_inicio, hora_fin = excluded.hora_fin, motivo = excluded.motivo",
            (user_id, bloque_id, fecha, tipo, hora_inicio, hora_fin, motivo),
        )


def borrar_excepcion(user_id, excepcion_id):
    with abrir() as conexion:
        conexion.execute("DELETE FROM excepcion_horario WHERE user_id = ? AND id = ?", (user_id, excepcion_id))


def excepciones_del_dia(user_id, fecha):
    """dict bloque_id -> excepcion."""
    with abrir() as conexion:
        filas = conexion.execute(
            "SELECT * FROM excepcion_horario WHERE user_id = ? AND fecha = ?", (user_id, fecha)
        ).fetchall()
    resultado = {}
    for fila in filas:
        resultado[fila["bloque_id"]] = fila
    return resultado


def excepciones_desde(user_id, fecha):
    """Excepciones de hoy en adelante, con el titulo del bloque."""
    with abrir() as conexion:
        return conexion.execute(
            "SELECT e.*, b.titulo, b.hora_inicio AS hora_inicio_normal, b.hora_fin AS hora_fin_normal "
            "FROM excepcion_horario e JOIN bloque_horario b ON b.id = e.bloque_id "
            "WHERE e.user_id = ? AND e.fecha >= ? ORDER BY e.fecha, b.hora_inicio",
            (user_id, fecha),
        ).fetchall()
