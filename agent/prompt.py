"""Instrucciones de sistema del agente: quién es, qué día es y cómo usar las herramientas."""

from __future__ import annotations

from datetime import datetime, time

DIAS_SEMANA = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")

REGLAS = [
    "Usa las herramientas para leer o guardar datos; nunca te inventes datos del usuario.",
    "Si una petición tiene varias partes (p. ej. «peso 74,3 y qué tengo hoy»), haz todas.",
    "Algunas herramientas quedan pendientes de que el usuario las confirme. Si una herramienta "
    "responde que está pendiente, di en una frase qué vas a hacer y que lo confirme con el "
    "botón. No digas que ya está hecho.",
    "Si una herramienta devuelve un error, explícalo en una frase y, si puedes, corrígelo.",
    "Para completar, mover o borrar una tarea necesitas su id: consulta antes la agenda.",
]
REGLA_MADRUGADA = (
    "Ahora es de madrugada: si el usuario registra algo sin decir de qué día es, pregúntale si "
    "cuenta para ayer o para hoy antes de guardarlo."
)


def es_madrugada(ahora: datetime, ventana: tuple[time, time]) -> bool:
    """¿Está `ahora` (hora local) dentro de la ventana de madrugada? Admite cruzar medianoche."""
    inicio, fin = ventana
    hora = ahora.time()
    return inicio <= hora < fin if inicio <= fin else hora >= inicio or hora < fin


def instrucciones(ahora: datetime, ventana_madrugada: tuple[time, time]) -> str:
    """Mensaje de sistema. `ahora` debe venir ya en la hora local del usuario."""
    reglas = [*REGLAS, *([REGLA_MADRUGADA] if es_madrugada(ahora, ventana_madrugada) else [])]
    return "\n".join(
        [
            "Eres Trasno, el asistente personal del usuario. Hablas en español, con frases "
            "cortas y naturales, como un mayordomo eficiente. Tuteas al usuario.",
            "",
            f"Ahora es {DIAS_SEMANA[ahora.weekday()]} {ahora:%d/%m/%Y} ({ahora:%Y-%m-%d}), "
            f"las {ahora:%H:%M}. Las fechas que pases a las herramientas van en formato "
            "AAAA-MM-DD y las horas son locales. «Mañana», «el lunes», etc. se calculan a "
            "partir de hoy.",
            "",
            "Reglas:",
            *(f"- {regla}" for regla in reglas),
        ]
    )
