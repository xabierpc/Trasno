"""Cálculos sobre el historial de sesiones: progreso, volumen semanal y récords personales."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum

from modules.training.domain.sesiones import Ejercicio, Sesion, normalizar_nombre


class TipoRecord(StrEnum):
    PESO = "peso"  # mayor peso levantado en una serie
    UN_RM = "1rm"  # mayor 1RM estimado
    VOLUMEN = "volumen"  # mayor volumen del ejercicio en un día


@dataclass(frozen=True)
class PuntoProgreso:
    """Resumen de un ejercicio en un día lógico."""

    logical_date: date
    un_rm: float
    peso_maximo: float
    volumen: float


@dataclass(frozen=True)
class Marca:
    """Un récord: el valor y el primer día en que se consiguió."""

    valor: float
    logical_date: date


@dataclass(frozen=True)
class RecordsEjercicio:
    """Récords personales de un ejercicio."""

    ejercicio: str
    peso: Marca
    un_rm: Marca
    volumen: Marca


@dataclass(frozen=True)
class RecordBatido:
    """Un récord que una sesión acaba de superar."""

    ejercicio: str
    tipo: TipoRecord
    valor: float
    anterior: float


def nombres_de_ejercicios(sesiones: Iterable[Sesion]) -> list[str]:
    """Ejercicios que aparecen en alguna sesión, por orden alfabético."""
    return sorted({e.nombre for sesion in sesiones for e in sesion.ejercicios})


def progreso(sesiones: Iterable[Sesion], ejercicio: str) -> list[PuntoProgreso]:
    """Un punto por día lógico en el que se hizo `ejercicio`, ordenado por fecha."""
    por_dia: dict[date, list[Ejercicio]] = defaultdict(list)
    for sesion in sesiones:
        por_dia[sesion.logical_date].extend(sesion.de(ejercicio))
    return [
        PuntoProgreso(
            logical_date=dia,
            un_rm=max(e.un_rm for e in hechos),
            peso_maximo=max(e.peso_maximo for e in hechos),
            volumen=sum(e.volumen for e in hechos),
        )
        for dia, hechos in sorted(por_dia.items())
        if hechos
    ]


def lunes_de(dia: date) -> date:
    """Lunes de la semana (ISO) a la que pertenece `dia`."""
    return dia - timedelta(days=dia.weekday())


def volumen_por_semana(sesiones: Iterable[Sesion]) -> list[tuple[date, float]]:
    """(lunes, volumen total) de cada semana con alguna sesión, ordenado por fecha."""
    semanas: dict[date, float] = defaultdict(float)
    for sesion in sesiones:
        semanas[lunes_de(sesion.logical_date)] += sesion.volumen
    return sorted(semanas.items())


def records_personales(sesiones: Iterable[Sesion]) -> list[RecordsEjercicio]:
    """Récords de cada ejercicio; en un empate gana el primer día en que se consiguió."""
    historial = list(sesiones)
    return [
        _records(nombre, progreso(historial, nombre)) for nombre in nombres_de_ejercicios(historial)
    ]


def records_batidos(sesion: Sesion, anteriores: Iterable[Sesion]) -> list[RecordBatido]:
    """Récords que `sesion` supera respecto a `anteriores`.

    La primera vez que se hace un ejercicio no cuenta: no hay marca previa que batir.
    """
    previos = {r.ejercicio: r for r in records_personales(anteriores)}
    batidos = []
    for nombre in dict.fromkeys(e.nombre for e in sesion.ejercicios):
        if nombre not in previos:
            continue
        (hoy,) = progreso([sesion], nombre)
        previo = previos[nombre]
        candidatos = [
            (TipoRecord.PESO, hoy.peso_maximo, previo.peso.valor),
            (TipoRecord.UN_RM, hoy.un_rm, previo.un_rm.valor),
            (TipoRecord.VOLUMEN, hoy.volumen, previo.volumen.valor),
        ]
        batidos += [
            RecordBatido(ejercicio=nombre, tipo=tipo, valor=valor, anterior=anterior)
            for tipo, valor, anterior in candidatos
            if valor > anterior
        ]
    return batidos


def _records(nombre: str, puntos: list[PuntoProgreso]) -> RecordsEjercicio:
    def mejor(valor_de: str) -> Marca:
        # max() devuelve el primero de los empatados y los puntos van por fecha
        punto = max(puntos, key=lambda p: getattr(p, valor_de))
        return Marca(valor=getattr(punto, valor_de), logical_date=punto.logical_date)

    return RecordsEjercicio(
        ejercicio=normalizar_nombre(nombre),
        peso=mejor("peso_maximo"),
        un_rm=mejor("un_rm"),
        volumen=mejor("volumen"),
    )
