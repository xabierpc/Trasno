"""Programador de trabajos periódicos: ejecuta los `add_job` de los módulos con APScheduler.

Corre en un hilo aparte dentro del proceso de la API: arranca y se para con ella (lifespan de
FastAPI). Si un trabajo falla, se registra en el log y no afecta a los demás.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.base import BaseTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from core.contracts import CadaDia, CadaIntervalo, Disparador

logger = logging.getLogger(__name__)

_DIAS_CRON = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


@dataclass(frozen=True)
class Trabajo:
    """Un trabajo registrado por un módulo con `ctx.add_job`."""

    nombre: str
    tarea: Callable[[], None]
    cuando: Disparador


class TrabajoDuplicado(ValueError):
    """Dos módulos han registrado un trabajo con el mismo nombre."""


class TrabajoNoEncontrado(KeyError):
    """No hay ningún trabajo con ese nombre."""


class Programador:
    """Envuelve un `BackgroundScheduler` de APScheduler con los disparadores de Trasno."""

    def __init__(self, trabajos: Iterable[Trabajo], zona: str) -> None:
        self._zona = ZoneInfo(zona)
        self._trabajos: dict[str, Trabajo] = {}
        for trabajo in trabajos:
            if trabajo.nombre in self._trabajos:
                raise TrabajoDuplicado(f"Hay dos trabajos llamados {trabajo.nombre!r}")
            self._trabajos[trabajo.nombre] = trabajo
        self._scheduler = BackgroundScheduler(timezone=self._zona)
        for trabajo in self._trabajos.values():
            self._scheduler.add_job(
                self._ejecutor(trabajo),
                trigger=self.trigger(trabajo.cuando),
                id=trabajo.nombre,
                name=trabajo.nombre,
                coalesce=True,  # si se perdieron varias ejecuciones, se hace solo una
                misfire_grace_time=300,  # hasta 5 min de retraso todavía se ejecuta
                max_instances=1,
            )

    @property
    def nombres(self) -> list[str]:
        return sorted(self._trabajos)

    def trigger(self, cuando: Disparador) -> BaseTrigger:
        """Traduce un disparador de Trasno a un trigger de APScheduler en la zona del usuario."""
        if isinstance(cuando, CadaDia):
            dias = ",".join(_DIAS_CRON[d] for d in sorted(cuando.dias)) if cuando.dias else "*"
            return CronTrigger(
                hour=cuando.hora.hour,
                minute=cuando.hora.minute,
                day_of_week=dias,
                timezone=self._zona,
            )
        if isinstance(cuando, CadaIntervalo):
            if cuando.minutos <= 0:
                raise ValueError(f"El intervalo debe ser > 0 minutos: {cuando.minutos}")
            return IntervalTrigger(minutes=cuando.minutos, timezone=self._zona)
        raise TypeError(f"Disparador desconocido: {cuando!r}")

    def proximas(self, ahora: datetime) -> dict[str, datetime | None]:
        """Próxima ejecución de cada trabajo a partir de `ahora` (calculada, no la del hilo)."""
        return {
            nombre: self.trigger(t.cuando).get_next_fire_time(None, ahora)
            for nombre, t in sorted(self._trabajos.items())
        }

    def ejecutar_ahora(self, nombre: str) -> None:
        """Ejecuta un trabajo en este mismo hilo, sin esperar a su hora (para probar)."""
        if nombre not in self._trabajos:
            raise TrabajoNoEncontrado(nombre)
        self._ejecutor(self._trabajos[nombre])()

    def arrancar(self) -> None:
        if not self._scheduler.running:
            self._scheduler.start()
            logger.info("Programador en marcha con %d trabajos", len(self._trabajos))

    def parar(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)

    @property
    def en_marcha(self) -> bool:
        return bool(self._scheduler.running)

    @staticmethod
    def _ejecutor(trabajo: Trabajo) -> Callable[[], None]:
        def ejecutar() -> None:
            try:
                trabajo.tarea()
            except Exception:
                logger.exception("El trabajo %s ha fallado", trabajo.nombre)

        return ejecutar
