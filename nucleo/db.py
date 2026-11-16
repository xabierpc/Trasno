"""Acceso a SQLite: un fichero .db por modulo dentro de data/."""

import sqlite3

from nucleo.config import DATA_DIR


def ruta_db(nombre):
    return DATA_DIR / (nombre + ".db")


def conectar(nombre):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conexion = sqlite3.connect(ruta_db(nombre))
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    conexion.execute("PRAGMA journal_mode = WAL")
    return conexion


def aplicar_esquema(nombre, ruta_sql, version):
    """Crea las tablas si la BD es nueva. La version se guarda en PRAGMA user_version."""
    sql = ruta_sql.read_text(encoding="utf-8")
    conexion = conectar(nombre)
    try:
        actual = conexion.execute("PRAGMA user_version").fetchone()[0]
        if actual == 0:
            conexion.executescript(sql)
            conexion.execute("PRAGMA user_version = " + str(int(version)))
        elif actual > version:
            raise RuntimeError(nombre + ".db es de una version mas nueva que el codigo")
        conexion.commit()
    finally:
        conexion.close()
