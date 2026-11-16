"""El Jarvis: nucleo que carga los modulos, guarda la configuracion y los coordina.

Los modulos no se importan entre si. Si uno necesita a otro, se lo pide al
Jarvis con obtener(nombre), que devuelve None si no esta instalado o activo.
"""

from pathlib import Path

from nucleo import config
from nucleo.db import aplicar_esquema, conectar
from nucleo.registro import descubrir


class Jarvis:

    def __init__(self, user_id=config.USUARIO_ACTUAL):
        self.user_id = user_id
        self.fecha_activa = None      # dia al que cuentan los registros (lo fija la interfaz)
        aplicar_esquema("core", Path(__file__).parent / "core.sql", 1)
        self._asegurar_usuario()
        self.modulos, self.errores = descubrir()
        for modulo in self.modulos.values():
            modulo.crear_bd()

    # ---------- usuario y configuracion ----------
    def _asegurar_usuario(self):
        conexion = conectar("core")
        try:
            conexion.execute(
                "INSERT OR IGNORE INTO usuario (id, nombre) VALUES (?, ?)",
                (self.user_id, config.NOMBRE_USUARIO_POR_DEFECTO),
            )
            for clave, valor in config.CONFIG_POR_DEFECTO.items():
                conexion.execute(
                    "INSERT OR IGNORE INTO configuracion (user_id, clave, valor) VALUES (?, ?, ?)",
                    (self.user_id, clave, valor),
                )
            conexion.commit()
        finally:
            conexion.close()

    def leer_config(self, clave):
        conexion = conectar("core")
        try:
            fila = conexion.execute(
                "SELECT valor FROM configuracion WHERE user_id = ? AND clave = ?",
                (self.user_id, clave),
            ).fetchone()
        finally:
            conexion.close()
        if fila is None:
            return config.CONFIG_POR_DEFECTO.get(clave)
        return fila["valor"]

    def guardar_config(self, clave, valor):
        conexion = conectar("core")
        try:
            conexion.execute(
                "INSERT INTO configuracion (user_id, clave, valor) VALUES (?, ?, ?) "
                "ON CONFLICT (user_id, clave) DO UPDATE SET valor = excluded.valor",
                (self.user_id, clave, str(valor)),
            )
            conexion.commit()
        finally:
            conexion.close()

    def sobrescribir_metricas(self):
        return self.leer_config("metricas.sobrescribir") == "1"

    # ---------- modulos ----------
    def esta_activo(self, nombre):
        if nombre not in self.modulos:
            return False
        conexion = conectar("core")
        try:
            fila = conexion.execute(
                "SELECT activo FROM estado_modulo WHERE user_id = ? AND modulo = ?",
                (self.user_id, nombre),
            ).fetchone()
        finally:
            conexion.close()
        if fila is None:
            return True
        return fila["activo"] == 1

    def activar(self, nombre, activo):
        valor = 0
        if activo:
            valor = 1
        conexion = conectar("core")
        try:
            conexion.execute(
                "INSERT INTO estado_modulo (user_id, modulo, activo) VALUES (?, ?, ?) "
                "ON CONFLICT (user_id, modulo) DO UPDATE SET activo = excluded.activo",
                (self.user_id, nombre, valor),
            )
            conexion.commit()
        finally:
            conexion.close()

    def activos(self):
        """Modulos activos cuyas dependencias tambien estan activas."""
        resultado = []
        for nombre in self.modulos:
            if self._usable(nombre):
                resultado.append(self.modulos[nombre])
        return resultado

    def _usable(self, nombre):
        if not self.esta_activo(nombre):
            return False
        for dependencia in self.modulos[nombre].dependencias:
            if not self._usable(dependencia):
                return False
        return True

    def obtener(self, nombre):
        """Otro modulo, o None si no esta instalado/activo."""
        if nombre in self.modulos and self._usable(nombre):
            return self.modulos[nombre]
        return None

    # ---------- coordinacion ----------
    def resumen_del_dia(self, fecha):
        resumen = []
        for modulo in self.activos():
            texto = modulo.resumen_diario(self, fecha)
            if texto is not None:
                resumen.append((modulo, texto))
        return resumen

    def ejecutar_tareas_periodicas(self):
        for modulo in self.activos():
            for tarea in modulo.tareas_periodicas(self):
                tarea()
