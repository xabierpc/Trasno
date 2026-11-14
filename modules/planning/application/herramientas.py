"""Herramientas de planning para el agente: agenda, tareas y eventos.

Crear, borrar y cambiar eventos o crear y borrar tareas requieren confirmación del usuario.
Completar o mover una tarea no: se deshace con la misma facilidad.
"""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from core.contracts import Tool
from modules.planning.application.casos_uso import CasosUsoPlanning
from modules.planning.domain.tareas import Prioridad


def herramientas_planning(casos: CasosUsoPlanning, zona: str) -> list[Tool]:
    """Las herramientas de planning sobre `casos`; las horas sin zona son de `zona`."""
    tz = ZoneInfo(zona)

    def local(instante: datetime) -> datetime:
        return instante if instante.tzinfo else instante.replace(tzinfo=tz)

    def agenda(dia: date) -> str:
        """Agenda de un día: clases y eventos con su hora, tareas (con su id) y atrasadas."""
        a = casos.agenda(dia)
        lineas = [f"Agenda del {dia:%d/%m/%Y}:"]
        lineas += [
            f"- {c.inicio:%H:%M}-{c.fin:%H:%M} {c.titulo}" + (f" ({c.lugar})" if c.lugar else "")
            for c in a.citas
        ] or ["- Sin citas."]
        lineas += [
            f"- Tarea [{t.id}] {t.titulo} · {t.prioridad.value}" + (" · hecha" if t.hecha else "")
            for t in a.tareas
        ] or ["- Sin tareas."]
        lineas += [f"- Atrasada [{t.id}] {t.titulo} (del {t.fecha:%d/%m})" for t in a.atrasadas]
        return "\n".join(lineas)

    def crear_tarea(
        titulo: str,
        fecha: date | None = None,
        prioridad: Prioridad = Prioridad.MEDIA,
        estimacion_min: int | None = None,
    ) -> str:
        """Crea una tarea para el día `fecha` (o sin día si no se indica)."""
        tarea = casos.crear_tarea(titulo, fecha, prioridad, estimacion_min)
        dia = f"para el {tarea.fecha:%d/%m/%Y}" if tarea.fecha else "sin fecha"
        return f"Tarea creada {dia}: {tarea.titulo} [{tarea.id}]."

    def completar_tarea(tarea_id: str) -> str:
        """Marca como hecha la tarea con ese id."""
        return f"Hecha: {casos.completar_tarea(tarea_id).titulo}."

    def mover_tarea(tarea_id: str, fecha: date | None) -> str:
        """Pasa la tarea con ese id a otro día (o a ninguno con null)."""
        tarea = casos.mover_tarea(tarea_id, fecha)
        return (
            f"Movida: {tarea.titulo} → {fecha:%d/%m/%Y}." if fecha else f"Sin día: {tarea.titulo}."
        )

    def borrar_tarea(tarea_id: str) -> str:
        """Borra la tarea con ese id."""
        casos.borrar_tarea(tarea_id)
        return "Tarea borrada."

    def crear_evento(titulo: str, inicio: datetime, fin: datetime, lugar: str | None = None) -> str:
        """Crea un evento con hora de inicio y de fin (AAAA-MM-DDTHH:MM, hora local)."""
        guardado = casos.crear_evento(titulo, local(inicio), local(fin), lugar)
        e = guardado.evento
        texto = (
            f"Evento creado: {e.titulo} el {local(inicio):%d/%m/%Y de %H:%M} a {local(fin):%H:%M}."
        )
        if guardado.avisos:
            texto += " Se pisa con: " + ", ".join(a.titulo for a in guardado.avisos) + "."
        return texto

    def borrar_evento(evento_id: str) -> str:
        """Borra el evento con ese id."""
        casos.borrar_evento(evento_id)
        return "Evento borrado."

    return [
        Tool(nombre="agenda", funcion=agenda),
        Tool(nombre="crear_tarea", funcion=crear_tarea, requiere_confirmacion=True),
        Tool(nombre="completar_tarea", funcion=completar_tarea),
        Tool(nombre="mover_tarea", funcion=mover_tarea),
        Tool(nombre="borrar_tarea", funcion=borrar_tarea, requiere_confirmacion=True),
        Tool(nombre="crear_evento", funcion=crear_evento, requiere_confirmacion=True),
        Tool(nombre="borrar_evento", funcion=borrar_evento, requiere_confirmacion=True),
    ]
