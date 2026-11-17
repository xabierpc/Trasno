"""Acceso a agenda.db (SQL). Solo habla con su propia BD.

Los nombres de columna que se usan en los UPDATE los pone siempre el servicio,
nunca el usuario.
"""

from contextlib import contextmanager

from nucleo.db import conectar

ABIERTAS = ("pendiente", "en_curso")


@contextmanager
def abrir():
    conexion = conectar("agenda")
    try:
        yield conexion
        conexion.commit()
    finally:
        conexion.close()


# ---------- tareas ----------
def crear_tarea(user_id, titulo, descripcion, fecha, fecha_limite, prioridad):
    with abrir() as conexion:
        cursor = conexion.execute(
            "INSERT INTO tarea (user_id, titulo, descripcion, fecha, fecha_limite, prioridad) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, titulo, descripcion, fecha, fecha_limite, prioridad),
        )
        return cursor.lastrowid


def actualizar_tarea(user_id, tarea_id, valores):
    asignaciones = ", ".join([columna + " = ?" for columna in valores])
    parametros = list(valores.values()) + [user_id, tarea_id]
    with abrir() as conexion:
        conexion.execute("UPDATE tarea SET " + asignaciones + " WHERE user_id = ? AND id = ?", parametros)


def borrar_tarea(user_id, tarea_id):
    with abrir() as conexion:
        conexion.execute("DELETE FROM tarea WHERE user_id = ? AND id = ?", (user_id, tarea_id))


def obtener_tarea(user_id, tarea_id):
    with abrir() as conexion:
        return conexion.execute("SELECT * FROM tarea WHERE user_id = ? AND id = ?", (user_id, tarea_id)).fetchone()


def listar_tareas(user_id, estados):
    huecos = ", ".join(["?"] * len(estados))
    with abrir() as conexion:
        return conexion.execute(
            "SELECT * FROM tarea WHERE user_id = ? AND estado IN (" + huecos + ") "
            "ORDER BY fecha IS NULL, fecha, prioridad, id",
            [user_id] + list(estados),
        ).fetchall()


def tareas_del_dia(user_id, fecha):
    """Planificadas para ese dia o que vencen ese dia (en cualquier estado)."""
    with abrir() as conexion:
        return conexion.execute(
            "SELECT * FROM tarea WHERE user_id = ? AND (fecha = ? OR fecha_limite = ?) "
            "ORDER BY prioridad, id",
            (user_id, fecha, fecha),
        ).fetchall()


def tareas_atrasadas(user_id, fecha):
    """Abiertas cuyo dia planificado o fecha limite ya ha pasado (y que no son de hoy)."""
    with abrir() as conexion:
        return conexion.execute(
            "SELECT * FROM tarea WHERE user_id = ? AND estado IN (?, ?) "
            "AND (fecha < ? OR fecha_limite < ?) "
            "AND COALESCE(fecha, '') <> ? AND COALESCE(fecha_limite, '') <> ? "
            "ORDER BY COALESCE(fecha_limite, fecha), prioridad",
            (user_id, ABIERTAS[0], ABIERTAS[1], fecha, fecha, fecha, fecha),
        ).fetchall()


# ---------- eventos ----------
def crear_evento(user_id, titulo, descripcion, inicio, fin, ubicacion):
    with abrir() as conexion:
        cursor = conexion.execute(
            "INSERT INTO evento (user_id, titulo, descripcion, inicio, fin, ubicacion) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, titulo, descripcion, inicio, fin, ubicacion),
        )
        return cursor.lastrowid


def actualizar_evento(user_id, evento_id, valores):
    asignaciones = ", ".join([columna + " = ?" for columna in valores])
    parametros = list(valores.values()) + [user_id, evento_id]
    with abrir() as conexion:
        conexion.execute("UPDATE evento SET " + asignaciones + " WHERE user_id = ? AND id = ?", parametros)


def borrar_evento(user_id, evento_id):
    with abrir() as conexion:
        conexion.execute("DELETE FROM evento WHERE user_id = ? AND id = ?", (user_id, evento_id))


def eventos_entre(user_id, desde, hasta):
    """Eventos que pisan el intervalo [desde, hasta). Textos 'YYYY-MM-DD HH:MM'."""
    with abrir() as conexion:
        return conexion.execute(
            "SELECT * FROM evento WHERE user_id = ? AND inicio < ? AND fin > ? ORDER BY inicio",
            (user_id, hasta, desde),
        ).fetchall()


# ---------- dias importantes ----------
def marcar_dia(user_id, fecha, nota):
    with abrir() as conexion:
        conexion.execute(
            "INSERT INTO dia_importante (user_id, fecha, nota) VALUES (?, ?, ?) "
            "ON CONFLICT (user_id, fecha) DO UPDATE SET nota = excluded.nota",
            (user_id, fecha, nota),
        )


def desmarcar_dia(user_id, fecha):
    with abrir() as conexion:
        conexion.execute("DELETE FROM dia_importante WHERE user_id = ? AND fecha = ?", (user_id, fecha))


def dias_importantes_entre(user_id, desde, hasta):
    """Dias marcados en [desde, hasta], ambos 'YYYY-MM-DD'."""
    with abrir() as conexion:
        return conexion.execute(
            "SELECT * FROM dia_importante WHERE user_id = ? AND fecha BETWEEN ? AND ? ORDER BY fecha",
            (user_id, desde, hasta),
        ).fetchall()
