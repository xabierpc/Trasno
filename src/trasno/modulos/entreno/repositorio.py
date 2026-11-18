"""Acceso a entreno.db (SQL). Solo habla con su propia BD.

Los nombres de columna que se usan en los UPDATE los pone siempre el servicio,
nunca el usuario.
"""

import sqlite3
from contextlib import contextmanager

from trasno.nucleo.db import conectar


@contextmanager
def abrir():
    conexion = conectar("entreno")
    try:
        yield conexion
        conexion.commit()
    finally:
        conexion.close()


class EnUso(Exception):
    """No se puede borrar porque hay datos que dependen de ello."""


# ======================================================================
# Ejercicios
# ======================================================================
def asegurar_ejercicio(user_id, nombre, tipo, grupo_muscular):
    with abrir() as conexion:
        conexion.execute(
            "INSERT OR IGNORE INTO ejercicio (user_id, nombre, tipo, grupo_muscular) VALUES (?, ?, ?, ?)",
            (user_id, nombre, tipo, grupo_muscular),
        )


def crear_ejercicio(user_id, nombre, tipo, grupo_muscular):
    with abrir() as conexion:
        cursor = conexion.execute(
            "INSERT INTO ejercicio (user_id, nombre, tipo, grupo_muscular) VALUES (?, ?, ?, ?)",
            (user_id, nombre, tipo, grupo_muscular),
        )
        return cursor.lastrowid


def borrar_ejercicio(user_id, ejercicio_id):
    try:
        with abrir() as conexion:
            conexion.execute("DELETE FROM ejercicio WHERE user_id = ? AND id = ?", (user_id, ejercicio_id))
    except sqlite3.IntegrityError:
        raise EnUso("ejercicio")


def listar_ejercicios(user_id):
    with abrir() as conexion:
        return conexion.execute(
            "SELECT * FROM ejercicio WHERE user_id = ? ORDER BY tipo DESC, nombre", (user_id,)
        ).fetchall()


def ejercicio_por_nombre(user_id, nombre):
    with abrir() as conexion:
        return conexion.execute(
            "SELECT * FROM ejercicio WHERE user_id = ? AND nombre = ?", (user_id, nombre)
        ).fetchone()


def obtener_ejercicio(user_id, ejercicio_id):
    with abrir() as conexion:
        return conexion.execute(
            "SELECT * FROM ejercicio WHERE user_id = ? AND id = ?", (user_id, ejercicio_id)
        ).fetchone()


# ======================================================================
# Rutinas (plan)
# ======================================================================
def crear_rutina(user_id, nombre):
    with abrir() as conexion:
        cursor = conexion.execute("INSERT INTO rutina (user_id, nombre) VALUES (?, ?)", (user_id, nombre))
        return cursor.lastrowid


def activar_rutina(user_id, rutina_id):
    """Solo una activa: se desactivan todas y se activa la elegida en la misma transaccion."""
    with abrir() as conexion:
        conexion.execute("UPDATE rutina SET activa = 0 WHERE user_id = ?", (user_id,))
        conexion.execute("UPDATE rutina SET activa = 1 WHERE user_id = ? AND id = ?", (user_id, rutina_id))


def borrar_rutina(user_id, rutina_id):
    with abrir() as conexion:
        conexion.execute("DELETE FROM rutina WHERE user_id = ? AND id = ?", (user_id, rutina_id))


def listar_rutinas(user_id):
    with abrir() as conexion:
        return conexion.execute(
            "SELECT * FROM rutina WHERE user_id = ? ORDER BY activa DESC, nombre", (user_id,)
        ).fetchall()


def rutina_activa(user_id):
    with abrir() as conexion:
        return conexion.execute(
            "SELECT * FROM rutina WHERE user_id = ? AND activa = 1", (user_id,)
        ).fetchone()


def dias_de_rutina(user_id, rutina_id):
    with abrir() as conexion:
        return conexion.execute(
            "SELECT * FROM rutina_dia WHERE user_id = ? AND rutina_id = ? ORDER BY dia_semana",
            (user_id, rutina_id),
        ).fetchall()


def dia_de_rutina(user_id, rutina_id, dia_semana):
    with abrir() as conexion:
        return conexion.execute(
            "SELECT * FROM rutina_dia WHERE user_id = ? AND rutina_id = ? AND dia_semana = ?",
            (user_id, rutina_id, dia_semana),
        ).fetchone()


def obtener_dia_rutina(user_id, rutina_dia_id):
    with abrir() as conexion:
        return conexion.execute(
            "SELECT d.*, r.nombre AS rutina FROM rutina_dia d JOIN rutina r ON r.id = d.rutina_id "
            "WHERE d.user_id = ? AND d.id = ?",
            (user_id, rutina_dia_id),
        ).fetchone()


def guardar_dia_rutina(user_id, rutina_id, dia_semana, nombre):
    with abrir() as conexion:
        conexion.execute(
            "INSERT INTO rutina_dia (user_id, rutina_id, dia_semana, nombre) VALUES (?, ?, ?, ?) "
            "ON CONFLICT (rutina_id, dia_semana) DO UPDATE SET nombre = excluded.nombre",
            (user_id, rutina_id, dia_semana, nombre),
        )


def borrar_dia_rutina(user_id, rutina_dia_id):
    with abrir() as conexion:
        conexion.execute("DELETE FROM rutina_dia WHERE user_id = ? AND id = ?", (user_id, rutina_dia_id))


def ejercicios_de_dia(user_id, rutina_dia_id):
    with abrir() as conexion:
        return conexion.execute(
            "SELECT re.*, e.nombre, e.tipo FROM rutina_ejercicio re "
            "JOIN ejercicio e ON e.id = re.ejercicio_id "
            "WHERE re.user_id = ? AND re.rutina_dia_id = ? ORDER BY re.orden",
            (user_id, rutina_dia_id),
        ).fetchall()


def anadir_a_dia(user_id, rutina_dia_id, ejercicio_id, series, reps, peso, duracion_s, distancia_m):
    with abrir() as conexion:
        orden = conexion.execute(
            "SELECT COALESCE(MAX(orden), 0) + 1 FROM rutina_ejercicio WHERE rutina_dia_id = ?", (rutina_dia_id,)
        ).fetchone()[0]
        conexion.execute(
            "INSERT INTO rutina_ejercicio (user_id, rutina_dia_id, ejercicio_id, orden, series_objetivo, "
            "reps_objetivo, peso_objetivo_kg, duracion_objetivo_s, distancia_objetivo_m) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, rutina_dia_id, ejercicio_id, orden, series, reps, peso, duracion_s, distancia_m),
        )


def quitar_de_dia(user_id, rutina_ejercicio_id):
    with abrir() as conexion:
        conexion.execute(
            "DELETE FROM rutina_ejercicio WHERE user_id = ? AND id = ?", (user_id, rutina_ejercicio_id)
        )


# ======================================================================
# Sesiones (registro)
# ======================================================================
def sesion_de(user_id, fecha):
    with abrir() as conexion:
        return conexion.execute(
            "SELECT * FROM sesion WHERE user_id = ? AND fecha = ? ORDER BY id LIMIT 1", (user_id, fecha)
        ).fetchone()


def crear_sesion(user_id, fecha, rutina_dia_id):
    with abrir() as conexion:
        cursor = conexion.execute(
            "INSERT INTO sesion (user_id, fecha, rutina_dia_id) VALUES (?, ?, ?)", (user_id, fecha, rutina_dia_id)
        )
        return cursor.lastrowid


def actualizar_sesion(user_id, sesion_id, valores):
    asignaciones = ", ".join([columna + " = ?" for columna in valores])
    parametros = list(valores.values()) + [user_id, sesion_id]
    with abrir() as conexion:
        conexion.execute("UPDATE sesion SET " + asignaciones + " WHERE user_id = ? AND id = ?", parametros)


def borrar_sesion(user_id, sesion_id):
    with abrir() as conexion:
        conexion.execute("DELETE FROM sesion WHERE user_id = ? AND id = ?", (user_id, sesion_id))


def series_de_sesion(user_id, sesion_id):
    with abrir() as conexion:
        return conexion.execute(
            "SELECT * FROM serie_fuerza WHERE user_id = ? AND sesion_id = ? ORDER BY ejercicio_id, orden",
            (user_id, sesion_id),
        ).fetchall()


def anadir_serie(user_id, sesion_id, ejercicio_id, reps, peso_kg, rpe):
    with abrir() as conexion:
        orden = conexion.execute(
            "SELECT COALESCE(MAX(orden), 0) + 1 FROM serie_fuerza WHERE sesion_id = ? AND ejercicio_id = ?",
            (sesion_id, ejercicio_id),
        ).fetchone()[0]
        conexion.execute(
            "INSERT INTO serie_fuerza (user_id, sesion_id, ejercicio_id, orden, reps, peso_kg, rpe) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, sesion_id, ejercicio_id, orden, reps, peso_kg, rpe),
        )


def borrar_serie(user_id, serie_id):
    with abrir() as conexion:
        conexion.execute("DELETE FROM serie_fuerza WHERE user_id = ? AND id = ?", (user_id, serie_id))


def cardio_de_sesion(user_id, sesion_id):
    with abrir() as conexion:
        return conexion.execute(
            "SELECT * FROM registro_cardio WHERE user_id = ? AND sesion_id = ? ORDER BY id", (user_id, sesion_id)
        ).fetchall()


def anadir_cardio(user_id, sesion_id, ejercicio_id, duracion_s, distancia_m, notas):
    with abrir() as conexion:
        conexion.execute(
            "INSERT INTO registro_cardio (user_id, sesion_id, ejercicio_id, duracion_s, distancia_m, notas) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, sesion_id, ejercicio_id, duracion_s, distancia_m, notas),
        )


def borrar_cardio(user_id, cardio_id):
    with abrir() as conexion:
        conexion.execute("DELETE FROM registro_cardio WHERE user_id = ? AND id = ?", (user_id, cardio_id))


def historial(user_id, limite):
    """Ultimas sesiones con totales de fuerza y cardio."""
    with abrir() as conexion:
        return conexion.execute(
            "SELECT s.id, s.fecha, s.notas, d.nombre AS dia, "
            "  (SELECT COUNT(*) FROM serie_fuerza f WHERE f.sesion_id = s.id) AS series, "
            "  (SELECT COALESCE(SUM(f.reps * f.peso_kg), 0) FROM serie_fuerza f WHERE f.sesion_id = s.id) AS volumen, "
            "  (SELECT COALESCE(SUM(c.duracion_s), 0) FROM registro_cardio c WHERE c.sesion_id = s.id) AS cardio_s, "
            "  (SELECT COALESCE(SUM(c.distancia_m), 0) FROM registro_cardio c WHERE c.sesion_id = s.id) AS cardio_m "
            "FROM sesion s LEFT JOIN rutina_dia d ON d.id = s.rutina_dia_id "
            "WHERE s.user_id = ? ORDER BY s.fecha DESC LIMIT ?",
            (user_id, limite),
        ).fetchall()


# ======================================================================
# PR
# ======================================================================
def mejor_marca(user_id, ejercicio_id, reps_minimas):
    """Mayor peso con al menos reps_minimas reps, juntando series registradas y PR manuales.

    Ante empate de peso gana la marca mas antigua (es cuando se consiguio).
    """
    with abrir() as conexion:
        return conexion.execute(
            "SELECT peso_kg, reps, fecha, origen FROM ("
            "  SELECT f.peso_kg, f.reps, s.fecha, 'registro' AS origen FROM serie_fuerza f "
            "  JOIN sesion s ON s.id = f.sesion_id WHERE f.user_id = ? AND f.ejercicio_id = ? "
            "  UNION ALL "
            "  SELECT peso_kg, reps, fecha, 'manual' AS origen FROM pr_manual WHERE user_id = ? AND ejercicio_id = ?"
            ") WHERE reps >= ? AND peso_kg > 0 ORDER BY peso_kg DESC, fecha ASC LIMIT 1",
            (user_id, ejercicio_id, user_id, ejercicio_id, reps_minimas),
        ).fetchone()


def crear_pr_manual(user_id, ejercicio_id, fecha, reps, peso_kg, notas):
    with abrir() as conexion:
        conexion.execute(
            "INSERT INTO pr_manual (user_id, ejercicio_id, fecha, reps, peso_kg, notas) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, ejercicio_id, fecha, reps, peso_kg, notas),
        )


def borrar_pr_manual(user_id, pr_id):
    with abrir() as conexion:
        conexion.execute("DELETE FROM pr_manual WHERE user_id = ? AND id = ?", (user_id, pr_id))


def prs_manuales(user_id):
    with abrir() as conexion:
        return conexion.execute(
            "SELECT p.*, e.nombre FROM pr_manual p JOIN ejercicio e ON e.id = p.ejercicio_id "
            "WHERE p.user_id = ? ORDER BY e.nombre, p.fecha DESC",
            (user_id,),
        ).fetchall()


def maximo_por_sesion(user_id, ejercicio_id):
    """Para la grafica de progreso: peso maximo de cada dia entrenado."""
    with abrir() as conexion:
        return conexion.execute(
            "SELECT s.fecha, MAX(f.peso_kg) AS peso_kg FROM serie_fuerza f JOIN sesion s ON s.id = f.sesion_id "
            "WHERE f.user_id = ? AND f.ejercicio_id = ? GROUP BY s.fecha ORDER BY s.fecha",
            (user_id, ejercicio_id),
        ).fetchall()
