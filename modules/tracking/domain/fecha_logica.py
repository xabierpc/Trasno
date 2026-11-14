"""Ventana de madrugada: decide si hay que preguntar a qué día cuenta un registro.

El dominio nunca elige la fecha lógica (es parámetro obligatorio de los casos de uso);
estas funciones solo ayudan a la interfaz o al agente a saber cuándo preguntar y qué ofrecer.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from modules.tracking.domain.errores import EntradaInvalida


def _hora_local(instante: datetime, zona: str | ZoneInfo) -> datetime:
    if instante.tzinfo is None or instante.utcoffset() is None:
        raise EntradaInvalida("El instante debe llevar zona horaria")
    tz = zona if isinstance(zona, ZoneInfo) else ZoneInfo(zona)
    return instante.astimezone(tz)


def es_madrugada(instante: datetime, ventana: tuple[time, time], zona: str | ZoneInfo) -> bool:
    """Indica si `instante`, en hora local, cae en la ventana [inicio, fin) de madrugada."""
    inicio, fin = ventana
    hora = _hora_local(instante, zona).time()
    if inicio <= fin:
        return inicio <= hora < fin
    return hora >= inicio or hora < fin  # ventana que cruza la medianoche


def opciones_fecha_logica(instante: datetime, zona: str | ZoneInfo) -> tuple[date, date]:
    """Devuelve (ayer, hoy) en hora local para preguntar al usuario."""
    hoy = _hora_local(instante, zona).date()
    return hoy - timedelta(days=1), hoy
