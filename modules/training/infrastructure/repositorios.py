"""Repositorio SQL de training: implementa el port sobre `training.sqlite`.

Cada operación abre su propia sesión de SQLAlchemy y hace commit al terminar, así que cuando
un método devuelve, el dato ya está guardado. Todas las consultas filtran por `user_id`.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Engine, delete, select
from sqlalchemy.orm import Session, selectinload

from modules.training.domain.sesiones import Ejercicio, Serie, Sesion
from modules.training.infrastructure.modelos import EjercicioRow, SerieRow, SesionRow


class RepositorioSesionesSQL:
    """Implementa `RepositorioSesiones` para un usuario."""

    def __init__(self, engine: Engine, user_id: int) -> None:
        self._engine = engine
        self._user_id = user_id

    def guardar(self, sesion: Sesion) -> None:
        with Session(self._engine) as session, session.begin():
            session.add(_fila(sesion, self._user_id))

    def listar(self, desde: date, hasta: date) -> list[Sesion]:
        consulta = (
            select(SesionRow)
            .where(
                SesionRow.user_id == self._user_id,
                SesionRow.logical_date.between(desde, hasta),
            )
            .options(selectinload(SesionRow.ejercicios).selectinload(EjercicioRow.series))
            .order_by(SesionRow.logical_date, SesionRow.timestamp)
        )
        with Session(self._engine) as session:
            return [_sesion(fila) for fila in session.scalars(consulta)]

    def borrar(self, sesion_id: str) -> bool:
        # Los ejercicios y las series caen por ON DELETE CASCADE (foreign_keys=ON).
        sentencia = delete(SesionRow).where(
            SesionRow.user_id == self._user_id, SesionRow.id == sesion_id
        )
        with Session(self._engine) as session, session.begin():
            return session.execute(sentencia).rowcount > 0


# --- Conversión fila ↔ dominio -----------------------------------------------------------


def _id() -> str:
    return str(uuid.uuid4())


def _fila(sesion: Sesion, user_id: int) -> SesionRow:
    return SesionRow(
        id=sesion.id,
        user_id=user_id,
        logical_date=sesion.logical_date,
        tipo=sesion.tipo,
        duracion_min=sesion.duracion_min,
        energia_previa=sesion.energia_previa,
        timestamp=sesion.timestamp,
        ejercicios=[
            EjercicioRow(
                id=_id(),
                user_id=user_id,
                orden=orden,
                nombre=ejercicio.nombre,
                series=[
                    SerieRow(
                        id=_id(),
                        user_id=user_id,
                        orden=n,
                        reps=serie.reps,
                        peso=serie.peso,
                        rpe=serie.rpe,
                    )
                    for n, serie in enumerate(ejercicio.series)
                ],
            )
            for orden, ejercicio in enumerate(sesion.ejercicios)
        ],
    )


def _sesion(fila: SesionRow) -> Sesion:
    return Sesion(
        id=fila.id,
        logical_date=fila.logical_date,
        tipo=fila.tipo,
        duracion_min=fila.duracion_min,
        energia_previa=fila.energia_previa,
        timestamp=fila.timestamp,
        ejercicios=tuple(
            Ejercicio(
                nombre=ejercicio.nombre,
                series=tuple(Serie(reps=s.reps, peso=s.peso, rpe=s.rpe) for s in ejercicio.series),
            )
            for ejercicio in fila.ejercicios
        ),
    )
