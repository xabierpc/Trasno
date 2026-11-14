"""Sección «Hoy» del briefing: citas, tareas pendientes y atrasadas del día."""

from __future__ import annotations

from datetime import date

from modules.planning.application.casos_uso import CasosUsoPlanning
from modules.planning.domain.tareas import Prioridad


class SeccionBriefingPlanning:
    """Implementa `SeccionBriefing` con la agenda del día."""

    titulo = "Hoy"
    orden = 10

    def __init__(self, casos: CasosUsoPlanning) -> None:
        self._casos = casos

    def lineas(self, dia: date) -> list[str]:
        agenda = self._casos.agenda(dia)
        lineas = []
        for cita in agenda.citas:
            lugar = f" · {cita.lugar}" if cita.lugar else ""
            lineas.append(f"**{cita.inicio:%H:%M}-{cita.fin:%H:%M}** {cita.titulo}{lugar}")
        for tarea in agenda.tareas:
            if not tarea.hecha:
                urgente = " (prioridad alta)" if tarea.prioridad is Prioridad.ALTA else ""
                lineas.append(f"Tarea: {tarea.titulo}{urgente}")
        if agenda.atrasadas:
            n = len(agenda.atrasadas)
            lineas.append(f"{n} tarea{'s' if n > 1 else ''} atrasada{'s' if n > 1 else ''}")
        return lineas or ["Sin citas ni tareas."]
