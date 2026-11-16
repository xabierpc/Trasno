"""Rutas y constantes globales de Trasno."""

from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATA_DIR = RAIZ / "data"
MODULOS_DIR = RAIZ / "modulos"

USUARIO_ACTUAL = 1
NOMBRE_USUARIO_POR_DEFECTO = "Genio"

CONFIG_POR_DEFECTO = {
    "metricas.sobrescribir": "1",   # misma metrica el mismo dia: 1 sobrescribe, 0 avisa
    "dia.hora_corte": "05:00",      # antes de esta hora se pregunta a que dia cuenta
}
