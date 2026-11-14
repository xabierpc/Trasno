"""Registro de acciones del agente sobre `core.sqlite`: implementa `RegistroAcciones`."""

from __future__ import annotations

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from core.contracts import Accion, EstadoAccion
from core.models import AgentLog


class AccionNoEncontrada(KeyError):
    """No hay ninguna acción con ese id para el usuario."""


class RegistroAccionesSQL:
    """Cada operación abre su sesión y hace commit; todas filtran por `user_id`."""

    def __init__(self, engine: Engine, user_id: int) -> None:
        self._engine = engine
        self._user_id = user_id

    def guardar(self, accion: Accion) -> Accion:
        fila = AgentLog(
            user_id=self._user_id,
            herramienta=accion.herramienta,
            argumentos=accion.argumentos,
            resultado=accion.resultado,
            timestamp=accion.timestamp,
            estado=accion.estado.value,
        )
        with Session(self._engine) as session, session.begin():
            session.add(fila)
            session.flush()
            return _accion(fila)

    def obtener(self, accion_id: int) -> Accion | None:
        with Session(self._engine) as session:
            fila = self._fila(session, accion_id)
            return None if fila is None else _accion(fila)

    def cambiar_estado(
        self, accion_id: int, estado: EstadoAccion, resultado: str | None = None
    ) -> Accion:
        with Session(self._engine) as session, session.begin():
            fila = self._fila(session, accion_id)
            if fila is None:
                raise AccionNoEncontrada(accion_id)
            fila.estado = estado.value
            fila.resultado = resultado
            return _accion(fila)

    def recientes(self, limite: int = 50) -> list[Accion]:
        consulta = (
            select(AgentLog)
            .where(AgentLog.user_id == self._user_id)
            .order_by(AgentLog.timestamp.desc(), AgentLog.id.desc())
            .limit(limite)
        )
        with Session(self._engine) as session:
            return [_accion(fila) for fila in session.scalars(consulta)]

    def _fila(self, session: Session, accion_id: int) -> AgentLog | None:
        fila = session.get(AgentLog, accion_id)
        return fila if fila is not None and fila.user_id == self._user_id else None


def _accion(fila: AgentLog) -> Accion:
    return Accion(
        id=fila.id,
        herramienta=fila.herramienta,
        argumentos=dict(fila.argumentos),
        estado=EstadoAccion(fila.estado),
        resultado=fila.resultado,
        timestamp=fila.timestamp,
    )
