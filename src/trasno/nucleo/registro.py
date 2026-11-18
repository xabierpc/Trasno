"""Descubre los modulos que hay en la carpeta modulos/."""

import importlib

from trasno.nucleo.config import MODULOS_DIR


def descubrir():
    """Devuelve (modulos, errores).

    modulos: dict nombre -> instancia, solo los que tienen sus dependencias.
    errores: dict carpeta -> motivo por el que no se ha cargado.
    """
    encontrados = {}
    errores = {}
    if not MODULOS_DIR.exists():
        return encontrados, errores

    for carpeta in sorted(MODULOS_DIR.iterdir()):
        if not carpeta.is_dir():
            continue
        if not (carpeta / "modulo.py").exists():
            continue
        try:
            codigo = importlib.import_module("trasno.modulos." + carpeta.name + ".modulo")
            instancia = codigo.crear(carpeta)
        except Exception as error:
            errores[carpeta.name] = "no se pudo cargar: " + str(error)
            continue
        encontrados[instancia.nombre] = instancia

    # Quitar los que no tienen sus dependencias (repetir hasta que no cambie nada).
    cambiado = True
    while cambiado:
        cambiado = False
        for nombre in list(encontrados):
            for dependencia in encontrados[nombre].dependencias:
                if dependencia not in encontrados:
                    errores[nombre] = "falta el modulo " + dependencia
                    del encontrados[nombre]
                    cambiado = True
                    break

    return encontrados, errores
