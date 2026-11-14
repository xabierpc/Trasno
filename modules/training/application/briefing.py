"""Sección «Entreno» del briefing: el último entreno y los de esta semana."""

from __future__ import annotations

from datetime import date, timedelta

from modules.training.application.casos_uso import CasosUsoTraining
from modules.training.domain.progreso import lunes_de

DIAS_ATRAS = 14


class SeccionBriefingTraining:
    """Implementa `SeccionBriefing` con el resumen de entrenos recientes."""

    titulo = "Entreno"
    orden = 30

    def __init__(self, casos: CasosUsoTraining) -> None:
        self._casos = casos

    def lineas(self, dia: date) -> list[str]:
        sesiones = self._casos.listar_sesiones(dia - timedelta(days=DIAS_ATRAS), dia)
        if not sesiones:
            return [f"Ningún entreno en los últimos {DIAS_ATRAS} días."]
        ultima = sesiones[-1]
        hace = (dia - ultima.logical_date).days
        cuando = {0: "hoy", 1: "ayer"}.get(hace, f"hace {hace} días")
        semana = sum(1 for s in sesiones if s.logical_date >= lunes_de(dia))
        return [
            f"Último entreno: {ultima.tipo}, {cuando}",
            f"Esta semana: {semana} sesi{'ón' if semana == 1 else 'ones'}",
        ]
