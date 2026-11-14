"""Repositorios SQL de planning: implementan los ports sobre `planning.sqlite`.

Cada operación abre su propia sesión de SQLAlchemy y hace commit al terminar, así que cuando
un método devuelve, el dato ya está guardado. Todas las consultas filtran por `user_id`.
`guardar` usa `session.merge`: inserta si el `id` no existe y actualiza si existe.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Engine, delete, select
from sqlalchemy.orm import Session

from modules.planning.domain.eventos import BloqueRecurrente, Evento, OrigenEvento
from modules.planning.domain.tareas import EstadoTarea, Prioridad, Tarea
from modules.planning.infrastructure.modelos import BloqueRow, EventoRow, TareaRow


class _RepositorioSQL:
    def __init__(self, engine: Engine, user_id: int) -> None:
        self._engine = engine
        self._user_id = user_id


# --- Tareas -----------------------------------------------------------------------------------


class RepositorioTareasSQL(_RepositorioSQL):
    """Implementa `RepositorioTareas` para un usuario."""

    def guardar(self, tarea: Tarea) -> None:
        with Session(self._engine) as session, session.begin():
            session.merge(_fila_tarea(tarea, self._user_id))

    def obtener(self, tarea_id: str) -> Tarea | None:
        return next(iter(self._consultar(TareaRow.id == tarea_id)), None)

    def del_dia(self, dia: date) -> list[Tarea]:
        return self._consultar(TareaRow.fecha == dia)

    def atrasadas(self, dia: date) -> list[Tarea]:
        return self._consultar(TareaRow.fecha < dia, TareaRow.estado == EstadoTarea.PENDIENTE.value)

    def sin_fecha(self) -> list[Tarea]:
        return self._consultar(TareaRow.fecha.is_(None))

    def borrar(self, tarea_id: str) -> bool:
        sentencia = delete(TareaRow).where(
            TareaRow.user_id == self._user_id, TareaRow.id == tarea_id
        )
        with Session(self._engine) as session, session.begin():
            return session.execute(sentencia).rowcount > 0

    def _consultar(self, *condiciones: object) -> list[Tarea]:
        consulta = (
            select(TareaRow)
            .where(TareaRow.user_id == self._user_id, *condiciones)  # type: ignore[arg-type]
            .order_by(TareaRow.fecha, TareaRow.creada_en)
        )
        with Session(self._engine) as session:
            return [_tarea(fila) for fila in session.scalars(consulta)]


def _fila_tarea(tarea: Tarea, user_id: int) -> TareaRow:
    return TareaRow(
        id=tarea.id,
        user_id=user_id,
        titulo=tarea.titulo,
        fecha=tarea.fecha,
        prioridad=tarea.prioridad.value,
        estimacion_min=tarea.estimacion_min,
        estado=tarea.estado.value,
        creada_en=tarea.creada_en,
        hecha_en=tarea.hecha_en,
    )


def _tarea(fila: TareaRow) -> Tarea:
    return Tarea(
        id=fila.id,
        titulo=fila.titulo,
        fecha=fila.fecha,
        prioridad=Prioridad(fila.prioridad),
        estimacion_min=fila.estimacion_min,
        estado=EstadoTarea(fila.estado),
        creada_en=fila.creada_en,
        hecha_en=fila.hecha_en,
    )


# --- Eventos ----------------------------------------------------------------------------------


class RepositorioEventosSQL(_RepositorioSQL):
    """Implementa `RepositorioEventos` para un usuario."""

    def guardar(self, evento: Evento) -> None:
        with Session(self._engine) as session, session.begin():
            session.merge(_fila_evento(evento, self._user_id))

    def obtener(self, evento_id: str) -> Evento | None:
        return next(iter(self._consultar(EventoRow.id == evento_id)), None)

    def por_uid(self, uid_externo: str) -> Evento | None:
        return next(iter(self._consultar(EventoRow.uid_externo == uid_externo)), None)

    def entre(self, inicio: datetime, fin: datetime) -> list[Evento]:
        return self._consultar(EventoRow.inicio < fin, EventoRow.fin > inicio)

    def borrar(self, evento_id: str) -> bool:
        sentencia = delete(EventoRow).where(
            EventoRow.user_id == self._user_id, EventoRow.id == evento_id
        )
        with Session(self._engine) as session, session.begin():
            return session.execute(sentencia).rowcount > 0

    def _consultar(self, *condiciones: object) -> list[Evento]:
        consulta = (
            select(EventoRow)
            .where(EventoRow.user_id == self._user_id, *condiciones)  # type: ignore[arg-type]
            .order_by(EventoRow.inicio, EventoRow.fin)
        )
        with Session(self._engine) as session:
            return [_evento(fila) for fila in session.scalars(consulta)]


def _fila_evento(evento: Evento, user_id: int) -> EventoRow:
    return EventoRow(
        id=evento.id,
        user_id=user_id,
        titulo=evento.titulo,
        inicio=evento.inicio,
        fin=evento.fin,
        lugar=evento.lugar,
        origen=evento.origen.value,
        uid_externo=evento.uid_externo,
    )


def _evento(fila: EventoRow) -> Evento:
    return Evento(
        id=fila.id,
        titulo=fila.titulo,
        inicio=fila.inicio,
        fin=fila.fin,
        lugar=fila.lugar,
        origen=OrigenEvento(fila.origen),
        uid_externo=fila.uid_externo,
    )


# --- Bloques ----------------------------------------------------------------------------------


class RepositorioBloquesSQL(_RepositorioSQL):
    """Implementa `RepositorioBloques` para un usuario."""

    def guardar(self, bloque: BloqueRecurrente) -> None:
        with Session(self._engine) as session, session.begin():
            session.merge(_fila_bloque(bloque, self._user_id))

    def obtener(self, bloque_id: str) -> BloqueRecurrente | None:
        return next(iter(self._consultar(BloqueRow.id == bloque_id)), None)

    def listar(self) -> list[BloqueRecurrente]:
        return self._consultar()

    def borrar(self, bloque_id: str) -> bool:
        sentencia = delete(BloqueRow).where(
            BloqueRow.user_id == self._user_id, BloqueRow.id == bloque_id
        )
        with Session(self._engine) as session, session.begin():
            return session.execute(sentencia).rowcount > 0

    def _consultar(self, *condiciones: object) -> list[BloqueRecurrente]:
        consulta = (
            select(BloqueRow)
            .where(BloqueRow.user_id == self._user_id, *condiciones)  # type: ignore[arg-type]
            .order_by(BloqueRow.dia_semana, BloqueRow.hora_inicio)
        )
        with Session(self._engine) as session:
            return [_bloque(fila) for fila in session.scalars(consulta)]


def _fila_bloque(bloque: BloqueRecurrente, user_id: int) -> BloqueRow:
    return BloqueRow(
        id=bloque.id,
        user_id=user_id,
        titulo=bloque.titulo,
        dia_semana=bloque.dia_semana,
        hora_inicio=bloque.hora_inicio,
        hora_fin=bloque.hora_fin,
        desde=bloque.desde,
        hasta=bloque.hasta,
        lugar=bloque.lugar,
    )


def _bloque(fila: BloqueRow) -> BloqueRecurrente:
    return BloqueRecurrente(
        id=fila.id,
        titulo=fila.titulo,
        dia_semana=fila.dia_semana,
        hora_inicio=fila.hora_inicio,
        hora_fin=fila.hora_fin,
        desde=fila.desde,
        hasta=fila.hasta,
        lugar=fila.lugar,
    )
