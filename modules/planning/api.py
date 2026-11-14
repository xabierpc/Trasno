"""Router FastAPI de planning: traduce HTTP ↔ casos de uso, sin lógica de negocio.

Las horas sin zona que lleguen (p. ej. "2026-11-16T09:00") se entienden en la zona del usuario,
para que la página y el agente no tengan que añadirla.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from datetime import UTC, date, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.routing import APIRoute
from pydantic import BaseModel, StrictInt

from core.contracts import Settings
from modules.planning.application.casos_uso import CasosUsoPlanning, EventoGuardado
from modules.planning.domain.agenda import Agenda, TipoCita
from modules.planning.domain.errores import (
    BloqueNoEncontrado,
    ErrorPlanning,
    EventoNoEncontrado,
    TareaNoEncontrada,
)
from modules.planning.domain.eventos import BloqueRecurrente, OrigenEvento
from modules.planning.domain.tareas import EstadoTarea, Prioridad, Tarea

# --- Modelos de entrada y salida --------------------------------------------------------------


class TareaEntrada(BaseModel):
    """Cuerpo de POST /planning/tasks. Sin `fecha`, la tarea va a la bandeja de entrada."""

    titulo: str
    fecha: date | None = None
    prioridad: Prioridad = Prioridad.MEDIA
    estimacion_min: StrictInt | None = None


class MoverTarea(BaseModel):
    """Cuerpo de POST /planning/tasks/{id}/move; `fecha` null la deja sin día."""

    fecha: date | None


class TareaSalida(BaseModel):
    id: str
    titulo: str
    fecha: date | None
    prioridad: Prioridad
    estimacion_min: int | None
    estado: EstadoTarea
    creada_en: datetime
    hecha_en: datetime | None


class EventoEntrada(BaseModel):
    """Cuerpo de POST /planning/events."""

    titulo: str
    inicio: datetime
    fin: datetime
    lugar: str | None = None


class MoverEvento(BaseModel):
    inicio: datetime
    fin: datetime


class EventoSalida(BaseModel):
    id: str
    titulo: str
    inicio: datetime
    fin: datetime
    lugar: str | None
    origen: OrigenEvento


class SolapeSalida(BaseModel):
    titulo: str
    inicio: datetime
    fin: datetime


class EventoGuardadoSalida(BaseModel):
    """Evento guardado y los avisos de solape (no impiden guardar)."""

    evento: EventoSalida
    avisos: list[SolapeSalida]


class BloqueEntrada(BaseModel):
    """Cuerpo de POST /planning/blocks. `dia_semana`: 0 = lunes … 6 = domingo; horas locales."""

    titulo: str
    dia_semana: StrictInt
    hora_inicio: time
    hora_fin: time
    desde: date | None = None
    hasta: date | None = None
    lugar: str | None = None


class BloqueSalida(BloqueEntrada):
    id: str


class BloqueGuardadoSalida(BaseModel):
    """Bloque guardado y los bloques con los que se pisa."""

    bloque: BloqueSalida
    avisos: list[BloqueSalida]


class ImportacionSalida(BaseModel):
    """Resultado de importar un .ics."""

    nuevos: int
    actualizados: int
    sin_cambios: int
    omitidos: list[str]


class CitaSalida(BaseModel):
    titulo: str
    inicio: datetime
    fin: datetime
    tipo: TipoCita
    id: str
    lugar: str | None


class AgendaSalida(BaseModel):
    """Agenda de un día: citas por hora, tareas del día y tareas atrasadas."""

    dia: date
    citas: list[CitaSalida]
    tareas: list[TareaSalida]
    atrasadas: list[TareaSalida]


# --- Errores de dominio → HTTP ----------------------------------------------------------------

_ESTADOS: dict[type[ErrorPlanning], int] = {
    TareaNoEncontrada: status.HTTP_404_NOT_FOUND,
    EventoNoEncontrado: status.HTTP_404_NOT_FOUND,
    BloqueNoEncontrado: status.HTTP_404_NOT_FOUND,
}


class _RutaPlanning(APIRoute):
    """Convierte los errores de dominio en respuestas HTTP: 404 o 422 (el resto)."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        original = super().get_route_handler()

        async def manejar(request: Request) -> Response:
            try:
                return await original(request)
            except ErrorPlanning as error:
                estado = _ESTADOS.get(type(error), status.HTTP_422_UNPROCESSABLE_CONTENT)
                raise HTTPException(status_code=estado, detail=str(error)) from error

        return manejar


def _ahora() -> datetime:
    return datetime.now(UTC)


# --- Router -----------------------------------------------------------------------------------


def crear_router(
    casos: CasosUsoPlanning,
    settings: Settings,
    reloj: Callable[[], datetime] = _ahora,
) -> APIRouter:
    """Crea el router /planning sobre los casos de uso recibidos."""
    router = APIRouter(prefix="/planning", tags=["planning"], route_class=_RutaPlanning)
    zona = ZoneInfo(settings.timezone)

    def con_zona(instante: datetime) -> datetime:
        return instante if instante.tzinfo is not None else instante.replace(tzinfo=zona)

    # --- Agenda ---

    @router.get("/agenda")
    def agenda(dia: date | None = None) -> AgendaSalida:
        """Agenda de `dia` (por defecto, hoy en la zona del usuario)."""
        return _agenda(casos.agenda(dia or reloj().astimezone(zona).date()), zona)

    # --- Tareas ---

    @router.post("/tasks", status_code=status.HTTP_201_CREATED)
    def crear_tarea(datos: TareaEntrada) -> TareaSalida:
        """Crea una tarea pendiente."""
        return _tarea(
            casos.crear_tarea(datos.titulo, datos.fecha, datos.prioridad, datos.estimacion_min)
        )

    @router.get("/tasks/inbox")
    def tareas_sin_fecha() -> list[TareaSalida]:
        """Tareas sin día asignado."""
        return [_tarea(t) for t in casos.tareas_sin_fecha()]

    @router.post("/tasks/{tarea_id}/complete")
    def completar_tarea(tarea_id: str) -> TareaSalida:
        """Marca una tarea como hecha."""
        return _tarea(casos.completar_tarea(tarea_id))

    @router.post("/tasks/{tarea_id}/reopen")
    def reabrir_tarea(tarea_id: str) -> TareaSalida:
        """Vuelve a dejar pendiente una tarea."""
        return _tarea(casos.reabrir_tarea(tarea_id))

    @router.post("/tasks/{tarea_id}/move")
    def mover_tarea(tarea_id: str, datos: MoverTarea) -> TareaSalida:
        """Pasa una tarea a otro día (o a ninguno)."""
        return _tarea(casos.mover_tarea(tarea_id, datos.fecha))

    @router.delete("/tasks/{tarea_id}", status_code=status.HTTP_204_NO_CONTENT)
    def borrar_tarea(tarea_id: str) -> None:
        """Borra una tarea (borrado real)."""
        casos.borrar_tarea(tarea_id)

    # --- Eventos ---

    @router.post("/events", status_code=status.HTTP_201_CREATED)
    def crear_evento(datos: EventoEntrada) -> EventoGuardadoSalida:
        """Guarda un evento y avisa de los solapes."""
        return _evento_guardado(
            casos.crear_evento(
                datos.titulo, con_zona(datos.inicio), con_zona(datos.fin), datos.lugar
            ),
            zona,
        )

    @router.post("/events/{evento_id}/move")
    def mover_evento(evento_id: str, datos: MoverEvento) -> EventoGuardadoSalida:
        """Cambia la hora de un evento y avisa de los solapes."""
        return _evento_guardado(
            casos.mover_evento(evento_id, con_zona(datos.inicio), con_zona(datos.fin)), zona
        )

    @router.delete("/events/{evento_id}", status_code=status.HTTP_204_NO_CONTENT)
    def borrar_evento(evento_id: str) -> None:
        """Borra un evento (borrado real)."""
        casos.borrar_evento(evento_id)

    @router.post("/import/ics")
    async def importar_ics(request: Request) -> ImportacionSalida:
        """Importa un calendario .ics enviado como cuerpo de la petición (text/calendar)."""
        resultado = casos.importar_calendario(await request.body())
        return ImportacionSalida(
            nuevos=resultado.nuevos,
            actualizados=resultado.actualizados,
            sin_cambios=resultado.sin_cambios,
            omitidos=resultado.omitidos,
        )

    # --- Bloques recurrentes ---

    @router.post("/blocks", status_code=status.HTTP_201_CREATED)
    def crear_bloque(datos: BloqueEntrada) -> BloqueGuardadoSalida:
        """Guarda un bloque semanal y avisa de los bloques con los que se pisa."""
        guardado = casos.crear_bloque(**datos.model_dump())
        return BloqueGuardadoSalida(
            bloque=_bloque(guardado.bloque), avisos=[_bloque(b) for b in guardado.avisos]
        )

    @router.get("/blocks")
    def listar_bloques() -> list[BloqueSalida]:
        """Todos los bloques recurrentes."""
        return [_bloque(b) for b in casos.listar_bloques()]

    @router.delete("/blocks/{bloque_id}", status_code=status.HTTP_204_NO_CONTENT)
    def borrar_bloque(bloque_id: str) -> None:
        """Borra un bloque recurrente."""
        casos.borrar_bloque(bloque_id)

    return router


# --- Conversión dominio → salida --------------------------------------------------------------


def _tarea(tarea: Tarea) -> TareaSalida:
    return TareaSalida(
        id=tarea.id,
        titulo=tarea.titulo,
        fecha=tarea.fecha,
        prioridad=tarea.prioridad,
        estimacion_min=tarea.estimacion_min,
        estado=tarea.estado,
        creada_en=tarea.creada_en,
        hecha_en=tarea.hecha_en,
    )


def _evento_guardado(guardado: EventoGuardado, zona: ZoneInfo) -> EventoGuardadoSalida:
    evento = guardado.evento
    return EventoGuardadoSalida(
        evento=EventoSalida(
            id=evento.id,
            titulo=evento.titulo,
            inicio=evento.inicio.astimezone(zona),
            fin=evento.fin.astimezone(zona),
            lugar=evento.lugar,
            origen=evento.origen,
        ),
        avisos=[
            SolapeSalida(
                titulo=a.titulo, inicio=a.inicio.astimezone(zona), fin=a.fin.astimezone(zona)
            )
            for a in guardado.avisos
        ],
    )


def _bloque(bloque: BloqueRecurrente) -> BloqueSalida:
    return BloqueSalida(
        id=bloque.id,
        titulo=bloque.titulo,
        dia_semana=bloque.dia_semana,
        hora_inicio=bloque.hora_inicio,
        hora_fin=bloque.hora_fin,
        desde=bloque.desde,
        hasta=bloque.hasta,
        lugar=bloque.lugar,
    )


def _agenda(agenda: Agenda, zona: ZoneInfo) -> AgendaSalida:
    return AgendaSalida(
        dia=agenda.dia,
        citas=[
            CitaSalida(
                titulo=c.titulo,
                inicio=c.inicio.astimezone(zona),
                fin=c.fin.astimezone(zona),
                tipo=c.tipo,
                id=c.id,
                lugar=c.lugar,
            )
            for c in agenda.citas
        ],
        tareas=[_tarea(t) for t in agenda.tareas],
        atrasadas=[_tarea(t) for t in agenda.atrasadas],
    )
