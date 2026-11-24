"""Acceso a dieta.db (SQL). Solo habla con su propia BD."""

from contextlib import contextmanager

from trasno.nucleo.db import conectar


@contextmanager
def abrir():
    conexion = conectar("dieta")
    try:
        yield conexion
        conexion.commit()
    finally:
        conexion.close()


def guardar(user_id, lunes, nombre, permitido):
    """Si ya estaba en la semana, cambia si/no."""
    with abrir() as conexion:
        conexion.execute(
            "INSERT INTO alimento (user_id, lunes, nombre, permitido) VALUES (?, ?, ?, ?) "
            "ON CONFLICT (user_id, lunes, nombre) DO UPDATE SET permitido = excluded.permitido",
            (user_id, lunes, nombre, permitido),
        )


def borrar(user_id, alimento_id):
    with abrir() as conexion:
        conexion.execute("DELETE FROM alimento WHERE user_id = ? AND id = ?", (user_id, alimento_id))


def de_semana(user_id, lunes):
    with abrir() as conexion:
        return conexion.execute(
            "SELECT * FROM alimento WHERE user_id = ? AND lunes = ? ORDER BY nombre COLLATE NOCASE",
            (user_id, lunes),
        ).fetchall()


def ultima_semana_antes(user_id, lunes):
    """Lunes de la semana mas reciente con datos anterior a lunes, o None."""
    with abrir() as conexion:
        fila = conexion.execute(
            "SELECT MAX(lunes) FROM alimento WHERE user_id = ? AND lunes < ?",
            (user_id, lunes),
        ).fetchone()
        return fila[0]


def copiar_semana(user_id, desde, hasta):
    """Copia los alimentos de la semana desde a la semana hasta (sin pisar los que ya haya)."""
    with abrir() as conexion:
        conexion.execute(
            "INSERT OR IGNORE INTO alimento (user_id, lunes, nombre, permitido) "
            "SELECT user_id, ?, nombre, permitido FROM alimento WHERE user_id = ? AND lunes = ?",
            (hasta, user_id, desde),
        )
