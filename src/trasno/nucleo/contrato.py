"""Contrato que cumple todo modulo (plugin) de Trasno.

Cada carpeta de modulos/ tiene un modulo.py con una funcion crear(carpeta)
que devuelve una instancia de una subclase de Modulo.
El nucleo solo conoce esta clase: nunca importa un modulo concreto.
"""

from trasno.nucleo.db import aplicar_esquema


class Modulo:
    nombre = ""              # identificador; tambien es el nombre de su .db
    titulo = ""              # lo que se ve en el menu
    icono = ""               # opcional; vacio = sin icono en el menu
    dependencias = ()        # modulos imprescindibles; sin ellos no se carga
    version_esquema = 1
    orden_inicio = 100       # posicion en la portada si implementa inicio() (menor = antes)

    def __init__(self, carpeta):
        self.carpeta = carpeta

    def crear_bd(self):
        ruta = self.carpeta / "schema.sql"
        if ruta.exists():
            aplicar_esquema(self.nombre, ruta, self.version_esquema)

    def pagina(self, jarvis):
        """Dibuja la pantalla del modulo con Streamlit."""
        raise NotImplementedError

    def inicio(self, jarvis, fecha):
        """Opcional: dibuja con Streamlit el bloque del modulo en la portada (Inicio).

        Si un modulo no lo sobrescribe, no aparece en Inicio.
        """
        raise NotImplementedError

    def tiene_inicio(self):
        return type(self).inicio is not Modulo.inicio

    def resumen_diario(self, jarvis, fecha):
        """Texto corto para la portada del Jarvis, o None si no hay nada."""
        return None

    def tareas_periodicas(self, jarvis):
        """Lista de funciones que el planificador ejecuta cada cierto tiempo."""
        return []
