"""Casos de uso de training. Cada método público es candidato a herramienta del agente."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from modules.training.application.ports import RepositorioSesiones
from modules.training.domain.errores import EjercicioNoEncontrado, SesionNoEncontrada
from modules.training.domain.progreso import (
    PuntoProgreso,
    RecordBatido,
    RecordsEjercicio,
    lunes_de,
    nombres_de_ejercicios,
    progreso,
    records_batidos,
    records_personales,
    volumen_por_semana,
)
from modules.training.domain.sesiones import Ejercicio, Sesion, normalizar_nombre


def _ahora() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class SesionGuardada:
    """Resultado de registrar una sesión: la sesión y los récords que ha batido."""

    sesion: Sesion
    records: list[RecordBatido]


class CasosUsoTraining:
    """Operaciones de training sobre el repositorio de sesiones de un usuario."""

    def __init__(
        self,
        sesiones: RepositorioSesiones,
        reloj: Callable[[], datetime] = _ahora,
        al_registrar: Callable[[Sesion], None] | None = None,
        al_borrar: Callable[[str], None] | None = None,
    ) -> None:
        self._sesiones = sesiones
        self._reloj = reloj
        self._al_registrar = al_registrar
        self._al_borrar = al_borrar

    def registrar_sesion(
        self,
        logical_date: date,
        tipo: str,
        ejercicios: Sequence[Ejercicio] = (),
        duracion_min: int | None = None,
        energia_previa: int | None = None,
        timestamp: datetime | None = None,
    ) -> SesionGuardada:
        """Guarda una sesión del día lógico `logical_date` y dice qué récords ha batido."""
        sesion = Sesion(
            logical_date=logical_date,
            tipo=tipo,
            ejercicios=tuple(ejercicios),
            duracion_min=duracion_min,
            energia_previa=energia_previa,
            timestamp=timestamp or self._reloj(),
        )
        anteriores = self._sesiones.listar(date.min, logical_date)
        self._sesiones.guardar(sesion)
        if self._al_registrar is not None:
            self._al_registrar(sesion)
        return SesionGuardada(sesion=sesion, records=records_batidos(sesion, anteriores))

    def listar_sesiones(self, desde: date, hasta: date) -> list[Sesion]:
        """Devuelve las sesiones entre `desde` y `hasta`, ambos incluidos."""
        return self._sesiones.listar(desde, hasta)

    def borrar_sesion(self, sesion_id: str) -> None:
        """Borra una sesión por su identificador (borrado real)."""
        if not self._sesiones.borrar(sesion_id):
            raise SesionNoEncontrada(sesion_id)
        if self._al_borrar is not None:
            self._al_borrar(sesion_id)

    def listar_ejercicios(self) -> list[str]:
        """Nombres de los ejercicios registrados alguna vez, por orden alfabético."""
        return nombres_de_ejercicios(self._todas())

    def progreso_ejercicio(self, nombre: str, desde: date, hasta: date) -> list[PuntoProgreso]:
        """1RM estimado, peso máximo y volumen del ejercicio por día entre `desde` y `hasta`."""
        if normalizar_nombre(nombre) not in self.listar_ejercicios():
            raise EjercicioNoEncontrado(nombre)
        return progreso(self._sesiones.listar(desde, hasta), nombre)

    def records(self) -> list[RecordsEjercicio]:
        """Récords personales (peso, 1RM estimado y volumen) de cada ejercicio."""
        return records_personales(self._todas())

    def volumen_semanal(self, desde: date, hasta: date) -> list[tuple[date, float]]:
        """(lunes, volumen) de las semanas completas cuyo lunes cae entre `desde` y `hasta`."""
        if hasta < desde:
            return []
        # Se lee hasta el domingo de la última semana para no dejarla a medias.
        semanas = volumen_por_semana(self._sesiones.listar(desde, _domingo_de(hasta)))
        return [(lunes, volumen) for lunes, volumen in semanas if desde <= lunes <= hasta]

    def _todas(self) -> list[Sesion]:
        return self._sesiones.listar(date.min, date.max)


def _domingo_de(dia: date) -> date:
    try:
        return lunes_de(dia) + timedelta(days=6)
    except OverflowError:  # `dia` está pegado a date.max
        return date.max
