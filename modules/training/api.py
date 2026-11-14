"""Router FastAPI de training: traduce HTTP ↔ casos de uso, sin lógica de negocio."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.routing import APIRoute
from pydantic import BaseModel, StrictInt

from modules.training.application.casos_uso import CasosUsoTraining
from modules.training.domain.errores import (
    EjercicioNoEncontrado,
    ErrorTraining,
    SesionNoEncontrada,
)
from modules.training.domain.progreso import Marca, TipoRecord
from modules.training.domain.sesiones import Ejercicio, Serie, Sesion


class SerieDatos(BaseModel):
    """Una serie: repeticiones, peso en kg y RPE opcional."""

    reps: StrictInt
    peso: float
    rpe: float | None = None


class EjercicioDatos(BaseModel):
    """Un ejercicio con sus series en orden."""

    nombre: str
    series: list[SerieDatos]


class SesionEntrada(BaseModel):
    """Cuerpo de POST /training/sessions; `logical_date` es obligatoria (regla 5)."""

    logical_date: date
    tipo: str
    duracion_min: StrictInt | None = None
    energia_previa: StrictInt | None = None
    timestamp: datetime | None = None
    ejercicios: list[EjercicioDatos] = []


class SesionSalida(BaseModel):
    """Una sesión tal como la devuelve la API, con su volumen ya calculado."""

    id: str
    logical_date: date
    tipo: str
    duracion_min: int | None
    energia_previa: int | None
    timestamp: datetime
    volumen: float
    ejercicios: list[EjercicioDatos]


class RecordBatidoSalida(BaseModel):
    """Un récord personal superado por la sesión recién registrada."""

    ejercicio: str
    tipo: TipoRecord
    valor: float
    anterior: float


class SesionRegistradaSalida(SesionSalida):
    """Respuesta de POST /training/sessions: la sesión y los récords que ha batido."""

    records: list[RecordBatidoSalida]


class PuntoProgresoSalida(BaseModel):
    """Resumen de un ejercicio en un día."""

    logical_date: date
    un_rm: float
    peso_maximo: float
    volumen: float


class MarcaSalida(BaseModel):
    valor: float
    logical_date: date


class RecordsSalida(BaseModel):
    """Récords personales de un ejercicio."""

    ejercicio: str
    peso: MarcaSalida
    un_rm: MarcaSalida
    volumen: MarcaSalida


class VolumenSemanaSalida(BaseModel):
    """Volumen total de una semana, identificada por su lunes."""

    semana: date
    volumen: float


_ESTADOS: dict[type[ErrorTraining], int] = {
    SesionNoEncontrada: status.HTTP_404_NOT_FOUND,
    EjercicioNoEncontrado: status.HTTP_404_NOT_FOUND,
}


class _RutaTraining(APIRoute):
    """Convierte los errores de dominio en respuestas HTTP: 404 o 422 (el resto)."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        original = super().get_route_handler()

        async def manejar(request: Request) -> Response:
            try:
                return await original(request)
            except ErrorTraining as error:
                estado = _ESTADOS.get(type(error), status.HTTP_422_UNPROCESSABLE_CONTENT)
                raise HTTPException(status_code=estado, detail=str(error)) from error

        return manejar


def crear_router(casos: CasosUsoTraining) -> APIRouter:
    """Crea el router /training sobre los casos de uso recibidos."""
    router = APIRouter(prefix="/training", tags=["training"], route_class=_RutaTraining)

    @router.post("/sessions", status_code=status.HTTP_201_CREATED)
    def registrar_sesion(datos: SesionEntrada) -> SesionRegistradaSalida:
        """Guarda una sesión con sus ejercicios y series; devuelve los récords batidos."""
        guardada = casos.registrar_sesion(
            logical_date=datos.logical_date,
            tipo=datos.tipo,
            ejercicios=[_ejercicio(e) for e in datos.ejercicios],
            duracion_min=datos.duracion_min,
            energia_previa=datos.energia_previa,
            timestamp=datos.timestamp,
        )
        records = [
            RecordBatidoSalida(
                ejercicio=r.ejercicio, tipo=r.tipo, valor=r.valor, anterior=r.anterior
            )
            for r in guardada.records
        ]
        return SesionRegistradaSalida(**_sesion(guardada.sesion).model_dump(), records=records)

    @router.get("/sessions")
    def listar_sesiones(desde: date = date.min, hasta: date = date.max) -> list[SesionSalida]:
        """Sesiones entre `desde` y `hasta` (ambos incluidos), de la más antigua a la más nueva."""
        return [_sesion(s) for s in casos.listar_sesiones(desde, hasta)]

    @router.delete("/sessions/{sesion_id}", status_code=status.HTTP_204_NO_CONTENT)
    def borrar_sesion(sesion_id: str) -> None:
        """Borra una sesión (borrado real)."""
        casos.borrar_sesion(sesion_id)

    @router.get("/exercises")
    def listar_ejercicios() -> list[str]:
        """Nombres de los ejercicios registrados alguna vez."""
        return casos.listar_ejercicios()

    @router.get("/exercises/{nombre}/progress")
    def progreso_ejercicio(
        nombre: str, desde: date = date.min, hasta: date = date.max
    ) -> list[PuntoProgresoSalida]:
        """1RM estimado, peso máximo y volumen del ejercicio por día."""
        return [
            PuntoProgresoSalida(
                logical_date=p.logical_date,
                un_rm=p.un_rm,
                peso_maximo=p.peso_maximo,
                volumen=p.volumen,
            )
            for p in casos.progreso_ejercicio(nombre, desde, hasta)
        ]

    @router.get("/records")
    def records() -> list[RecordsSalida]:
        """Récords personales de cada ejercicio."""
        return [
            RecordsSalida(
                ejercicio=r.ejercicio,
                peso=_marca(r.peso),
                un_rm=_marca(r.un_rm),
                volumen=_marca(r.volumen),
            )
            for r in casos.records()
        ]

    @router.get("/weekly-volume")
    def volumen_semanal(
        desde: date = date.min, hasta: date = date.max
    ) -> list[VolumenSemanaSalida]:
        """Volumen total de cada semana cuyo lunes cae entre `desde` y `hasta`."""
        return [
            VolumenSemanaSalida(semana=lunes, volumen=volumen)
            for lunes, volumen in casos.volumen_semanal(desde, hasta)
        ]

    return router


def _ejercicio(datos: EjercicioDatos) -> Ejercicio:
    return Ejercicio(
        nombre=datos.nombre,
        series=tuple(Serie(reps=s.reps, peso=s.peso, rpe=s.rpe) for s in datos.series),
    )


def _sesion(sesion: Sesion) -> SesionSalida:
    return SesionSalida(
        id=sesion.id,
        logical_date=sesion.logical_date,
        tipo=sesion.tipo,
        duracion_min=sesion.duracion_min,
        energia_previa=sesion.energia_previa,
        timestamp=sesion.timestamp,
        volumen=sesion.volumen,
        ejercicios=[
            EjercicioDatos(
                nombre=e.nombre,
                series=[SerieDatos(reps=s.reps, peso=s.peso, rpe=s.rpe) for s in e.series],
            )
            for e in sesion.ejercicios
        ],
    )


def _marca(marca: Marca) -> MarcaSalida:
    return MarcaSalida(valor=marca.valor, logical_date=marca.logical_date)
