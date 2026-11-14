"""Casos de uso de tracking. Cada método público es candidato a herramienta del agente."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, date, datetime

from modules.tracking.application.ports import RepositorioEntradas, RepositorioMetricas
from modules.tracking.domain.errores import (
    EntradaNoEncontrada,
    MetricaDuplicada,
    MetricaNoEncontrada,
)
from modules.tracking.domain.metricas import (
    Agregacion,
    MetricDefinition,
    MetricEntry,
    PoliticaDuplicado,
    TipoMetrica,
)
from modules.tracking.domain.rachas import ResumenRacha, resumir_racha


def _ahora() -> datetime:
    return datetime.now(UTC)


class CasosUsoTracking:
    """Operaciones de tracking sobre los repositorios de un usuario."""

    def __init__(
        self,
        metricas: RepositorioMetricas,
        entradas: RepositorioEntradas,
        reloj: Callable[[], datetime] = _ahora,
        al_registrar: Callable[[MetricDefinition, MetricEntry], None] | None = None,
    ) -> None:
        self._metricas = metricas
        self._entradas = entradas
        self._reloj = reloj
        self._al_registrar = al_registrar

    def crear_metrica(
        self,
        nombre: str,
        unidad: str,
        tipo: TipoMetrica,
        agregacion: Agregacion = Agregacion.ULTIMA,
        on_duplicate: PoliticaDuplicado = PoliticaDuplicado.REPLACE,
        objetivo: float | None = None,
        minimo: float | None = None,
        maximo: float | None = None,
        escala_max: int | None = None,
        categorias: tuple[str, ...] = (),
        activa: bool = True,
    ) -> MetricDefinition:
        """Crea una métrica nueva; el nombre no puede repetirse."""
        if self._metricas.por_nombre(nombre) is not None:
            raise MetricaDuplicada(nombre)
        definicion = MetricDefinition(
            nombre=nombre,
            unidad=unidad,
            tipo=tipo,
            agregacion=agregacion,
            on_duplicate=on_duplicate,
            objetivo=objetivo,
            minimo=minimo,
            maximo=maximo,
            escala_max=escala_max,
            categorias=categorias,
            activa=activa,
        )
        self._metricas.guardar(definicion)
        return definicion

    def listar_metricas(self, solo_activas: bool = False) -> list[MetricDefinition]:
        """Devuelve las métricas definidas (o solo las activas), por orden alfabético."""
        return [m for m in self._metricas.listar() if m.activa or not solo_activas]

    def activar_metrica(self, nombre: str, activa: bool) -> MetricDefinition:
        """Activa o desactiva una métrica; desactivarla no borra sus entradas."""
        definicion = replace(self._definicion(nombre), activa=activa)
        self._metricas.actualizar(definicion)
        return definicion

    def registrar_metrica(
        self,
        nombre: str,
        valor: object,
        logical_date: date,
        timestamp: datetime | None = None,
    ) -> MetricEntry:
        """Guarda un valor de la métrica `nombre` para el día lógico `logical_date`."""
        definicion = self._definicion(nombre)
        slot = (
            self._entradas.siguiente_slot(definicion.id, logical_date)
            if definicion.on_duplicate is PoliticaDuplicado.KEEP_ALL
            else 0  # replace: siempre el slot 0, y guardar() hace upsert
        )
        entrada = definicion.crear_entrada(
            valor, timestamp=timestamp or self._reloj(), logical_date=logical_date, slot=slot
        )
        guardada = self._entradas.guardar(entrada)
        if self._al_registrar is not None:
            self._al_registrar(definicion, guardada)
        return guardada

    def listar_entradas(self, nombre: str, desde: date, hasta: date) -> list[MetricEntry]:
        """Devuelve las entradas de la métrica entre `desde` y `hasta`, ambos incluidos."""
        return self._entradas.listar(self._definicion(nombre).id, desde, hasta)

    def borrar_entrada(self, entrada_id: str) -> None:
        """Borra una entrada por su identificador (borrado real)."""
        if not self._entradas.borrar(entrada_id):
            raise EntradaNoEncontrada(entrada_id)

    def racha(self, nombre: str, hoy: date) -> ResumenRacha:
        """Racha actual y máxima de la métrica y su cumplimiento de 7 y 30 días hasta `hoy`."""
        definicion = self._definicion(nombre)
        entradas = self._entradas.listar(definicion.id, date.min, hoy)
        return resumir_racha(definicion, entradas, hoy)

    def _definicion(self, nombre: str) -> MetricDefinition:
        definicion = self._metricas.por_nombre(nombre)
        if definicion is None:
            raise MetricaNoEncontrada(nombre)
        return definicion
