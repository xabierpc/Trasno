"""Sección «Seguimiento» del briefing: el peso y las rachas de hábitos."""

from __future__ import annotations

from datetime import date, timedelta
from statistics import mean

from modules.tracking.application.casos_uso import CasosUsoTracking
from modules.tracking.domain.errores import MetricaNoEncontrada
from modules.tracking.domain.metricas import TipoMetrica

RACHA_MINIMA = 2  # una racha de 1 día no merece mención


def cuando(dia: date, hoy: date) -> str:
    """«hoy», «ayer» o «el 12/11»."""
    if dia == hoy:
        return "hoy"
    if dia == hoy - timedelta(days=1):
        return "ayer"
    return f"el {dia:%d/%m}"


def numero(valor: float) -> str:
    """74.3 → «74,3»; 75.0 → «75»."""
    return f"{valor:.1f}".rstrip("0").rstrip(".").replace(".", ",")


class SeccionBriefingTracking:
    """Implementa `SeccionBriefing` con el último peso y las rachas en curso."""

    titulo = "Seguimiento"
    orden = 20

    def __init__(self, casos: CasosUsoTracking) -> None:
        self._casos = casos

    def lineas(self, dia: date) -> list[str]:
        return [*self._peso(dia), *self._rachas(dia)]

    def _peso(self, dia: date) -> list[str]:
        try:
            entradas = self._casos.listar_entradas("peso", dia - timedelta(days=30), dia)
        except MetricaNoEncontrada:
            return []
        if not entradas:
            return []
        ultima = max(entradas, key=lambda e: (e.logical_date, e.slot))
        linea = f"Peso: **{numero(float(ultima.valor))} kg** ({cuando(ultima.logical_date, dia)})"
        semana = [float(e.valor) for e in entradas if e.logical_date > dia - timedelta(days=7)]
        if len(semana) >= 2:
            linea += f" · media de 7 días {numero(mean(semana))} kg"
        return [linea]

    def _rachas(self, dia: date) -> list[str]:
        lineas = []
        for metrica in self._casos.listar_metricas(solo_activas=True):
            if metrica.tipo is not TipoMetrica.BOOLEANA:
                continue
            racha = self._casos.racha(metrica.nombre, dia).racha.actual
            if racha >= RACHA_MINIMA:
                lineas.append(f"Racha de {metrica.nombre}: {racha} días")
        return lineas
