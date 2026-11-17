"""Regla de madrugada: antes de la hora de corte, se pregunta a que dia cuenta el registro."""

from datetime import date, datetime, timedelta

DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
DIAS_CORTOS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
         "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]


def a_fecha(texto):
    """'YYYY-MM-DD' -> date."""
    return date.fromisoformat(texto)


def lunes_de(dia):
    """Lunes de la semana de dia (date)."""
    return dia - timedelta(days=dia.weekday())


def dia_bonito(texto):
    """'2026-11-17' -> 'Mar 17/11'."""
    dia = a_fecha(texto)
    return DIAS_CORTOS[dia.weekday()] + " " + dia.strftime("%d/%m")


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
