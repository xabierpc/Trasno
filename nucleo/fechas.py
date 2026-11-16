"""Regla de madrugada: antes de la hora de corte, se pregunta a que dia cuenta el registro."""

from datetime import datetime, timedelta


def es_madrugada(ahora, hora_corte):
    partes = hora_corte.split(":")
    corte = ahora.replace(hour=int(partes[0]), minute=int(partes[1]), second=0, microsecond=0)
    return ahora < corte


def opciones_de_dia(ahora=None):
    """Devuelve (hoy, ayer) como fechas 'YYYY-MM-DD'."""
    if ahora is None:
        ahora = datetime.now()
    hoy = ahora.date()
    ayer = hoy - timedelta(days=1)
    return hoy.isoformat(), ayer.isoformat()
