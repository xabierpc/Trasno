"""Repositorios SQL de tracking: implementan los ports sobre `tracking.sqlite`.

Cada operación abre su propia sesión y hace commit al terminar, así que cuando un método
devuelve, el dato ya está guardado. Todas las consultas filtran por `user_id`.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date

from sqlalchemy import Engine, delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from modules.tracking.domain.errores import MetricaDuplicada
from modules.tracking.domain.metricas import (
    Agregacion,
    MetricDefinition,
    MetricEntry,
    PoliticaDuplicado,
    TipoMetrica,
    ValorMetrica,
)
from modules.tracking.infrastructure.modelos import MetricDefinitionRow, MetricEntryRow

_ENTEROS = {TipoMetrica.DURACION, TipoMetrica.ESCALA, TipoMetrica.CONTEO}


class RepositorioMetricasSQL:
    """Implementa `RepositorioMetricas` para un usuario."""

    def __init__(self, engine: Engine, user_id: int) -> None:
        self._engine = engine
        self._user_id = user_id

    def guardar(self, definicion: MetricDefinition) -> None:
        try:
            with Session(self._engine) as session, session.begin():
                session.add(_fila_definicion(definicion, self._user_id))
        except IntegrityError as error:
            raise MetricaDuplicada(definicion.nombre) from error

    def por_nombre(self, nombre: str) -> MetricDefinition | None:
        consulta = select(MetricDefinitionRow).where(
            MetricDefinitionRow.user_id == self._user_id, MetricDefinitionRow.nombre == nombre
        )
        with Session(self._engine) as session:
            fila = session.scalars(consulta).one_or_none()
            return None if fila is None else _definicion(fila)

    def listar(self) -> list[MetricDefinition]:
        consulta = (
            select(MetricDefinitionRow)
            .where(MetricDefinitionRow.user_id == self._user_id)
            .order_by(MetricDefinitionRow.nombre)
        )
        with Session(self._engine) as session:
            return [_definicion(fila) for fila in session.scalars(consulta)]


class RepositorioEntradasSQL:
    """Implementa `RepositorioEntradas` para un usuario."""

    def __init__(self, engine: Engine, user_id: int) -> None:
        self._engine = engine
        self._user_id = user_id

    def guardar(self, entrada: MetricEntry) -> MetricEntry:
        num, texto = _a_columnas(entrada.valor)
        with Session(self._engine) as session, session.begin():
            fila = session.scalars(
                select(MetricEntryRow).where(
                    MetricEntryRow.user_id == self._user_id,
                    MetricEntryRow.metric_id == entrada.metric_id,
                    MetricEntryRow.logical_date == entrada.logical_date,
                    MetricEntryRow.slot == entrada.slot,
                )
            ).one_or_none()
            if fila is None:
                fila = MetricEntryRow(
                    id=entrada.id,
                    user_id=self._user_id,
                    metric_id=entrada.metric_id,
                    logical_date=entrada.logical_date,
                    slot=entrada.slot,
                )
                session.add(fila)
            fila.valor_num, fila.valor_texto, fila.timestamp = num, texto, entrada.timestamp
            return replace(entrada, id=fila.id)

    def siguiente_slot(self, metric_id: str, logical_date: date) -> int:
        consulta = select(func.max(MetricEntryRow.slot)).where(
            MetricEntryRow.user_id == self._user_id,
            MetricEntryRow.metric_id == metric_id,
            MetricEntryRow.logical_date == logical_date,
        )
        with Session(self._engine) as session:
            maximo = session.scalar(consulta)
            return 0 if maximo is None else maximo + 1

    def listar(self, metric_id: str, desde: date, hasta: date) -> list[MetricEntry]:
        consulta = (
            select(MetricEntryRow, MetricDefinitionRow.tipo)
            .join(MetricDefinitionRow, MetricDefinitionRow.id == MetricEntryRow.metric_id)
            .where(
                MetricEntryRow.user_id == self._user_id,
                MetricEntryRow.metric_id == metric_id,
                MetricEntryRow.logical_date.between(desde, hasta),
            )
            .order_by(MetricEntryRow.logical_date, MetricEntryRow.slot)
        )
        with Session(self._engine) as session:
            return [_entrada(fila, TipoMetrica(tipo)) for fila, tipo in session.execute(consulta)]

    def borrar(self, entrada_id: str) -> bool:
        sentencia = delete(MetricEntryRow).where(
            MetricEntryRow.user_id == self._user_id, MetricEntryRow.id == entrada_id
        )
        with Session(self._engine) as session, session.begin():
            return session.execute(sentencia).rowcount > 0


# --- Conversión fila ↔ dominio -----------------------------------------------------------


def _fila_definicion(definicion: MetricDefinition, user_id: int) -> MetricDefinitionRow:
    return MetricDefinitionRow(
        id=definicion.id,
        user_id=user_id,
        nombre=definicion.nombre,
        unidad=definicion.unidad,
        tipo=definicion.tipo.value,
        agregacion=definicion.agregacion.value,
        on_duplicate=definicion.on_duplicate.value,
        objetivo=definicion.objetivo,
        minimo=definicion.minimo,
        maximo=definicion.maximo,
        escala_max=definicion.escala_max,
        categorias=list(definicion.categorias),
    )


def _definicion(fila: MetricDefinitionRow) -> MetricDefinition:
    return MetricDefinition(
        id=fila.id,
        nombre=fila.nombre,
        unidad=fila.unidad,
        tipo=TipoMetrica(fila.tipo),
        agregacion=Agregacion(fila.agregacion),
        on_duplicate=PoliticaDuplicado(fila.on_duplicate),
        objetivo=fila.objetivo,
        minimo=fila.minimo,
        maximo=fila.maximo,
        escala_max=fila.escala_max,
        categorias=tuple(fila.categorias),
    )


def _a_columnas(valor: ValorMetrica) -> tuple[float | None, str | None]:
    """Reparte el valor entre (valor_num, valor_texto); un bool se guarda como 0/1."""
    if isinstance(valor, str):
        return None, valor
    return float(valor), None


def _de_columnas(fila: MetricEntryRow, tipo: TipoMetrica) -> ValorMetrica:
    """Reconstruye el valor de dominio según el tipo de la métrica."""
    if tipo is TipoMetrica.CATEGORICA:
        assert fila.valor_texto is not None
        return fila.valor_texto
    assert fila.valor_num is not None
    if tipo is TipoMetrica.BOOLEANA:
        return fila.valor_num != 0
    return int(fila.valor_num) if tipo in _ENTEROS else fila.valor_num


def _entrada(fila: MetricEntryRow, tipo: TipoMetrica) -> MetricEntry:
    return MetricEntry(
        id=fila.id,
        metric_id=fila.metric_id,
        valor=_de_columnas(fila, tipo),
        timestamp=fila.timestamp,
        logical_date=fila.logical_date,
        slot=fila.slot,
    )
