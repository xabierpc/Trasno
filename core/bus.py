"""Bus de eventos síncrono en memoria: implementa `core.contracts.EventBus`."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, TypeVar

from sqlalchemy import event as sa_event
from sqlalchemy.orm import Session, SessionTransaction

from core.contracts import Event, EventBus

logger = logging.getLogger(__name__)

E = TypeVar("E", bound=Event)

_PENDIENTES = "trasno_eventos_pendientes"


class InMemoryEventBus:
    """Entrega cada evento, en orden de suscripción, a los handlers de su tipo o de sus bases."""

    def __init__(self) -> None:
        self._suscripciones: tuple[tuple[type[Event], Callable[[Any], None]], ...] = ()

    def subscribe(self, event_type: type[E], handler: Callable[[E], None]) -> None:
        """Registra `handler` para `event_type` y sus subclases."""
        # Se sustituye la tupla entera: publish nunca ve una lista a medio modificar.
        self._suscripciones = (*self._suscripciones, (event_type, handler))

    def publish(self, event: Event) -> None:
        """Llama a cada handler suscrito; si uno falla, lo registra y sigue con el resto."""
        for event_type, handler in self._suscripciones:
            if not isinstance(event, event_type):
                continue
            try:
                handler(event)
            except Exception:
                logger.exception("El handler %r falló procesando %s", handler, type(event).__name__)


def publicar_tras_commit(session: Session, bus: EventBus, event: Event) -> None:
    """Publica `event` en `bus` cuando `session` haga commit; se descarta si hay rollback."""
    # Liga el evento a la transacción actual; si aún no hay, la inicia (como haría una query).
    session.connection()
    if _PENDIENTES not in session.info:
        session.info[_PENDIENTES] = []
        sa_event.listen(session, "after_commit", _publicar_pendientes)
        # after_soft_rollback se dispara aunque la sesión no llegara a tocar la BD.
        sa_event.listen(session, "after_soft_rollback", _descartar_pendientes)
    session.info[_PENDIENTES].append((bus, event))


def _publicar_pendientes(session: Session) -> None:
    pendientes: list[tuple[EventBus, Event]] = session.info[_PENDIENTES]
    session.info[_PENDIENTES] = []
    for bus, event in pendientes:
        bus.publish(event)


def _descartar_pendientes(session: Session, previous_transaction: SessionTransaction) -> None:
    # Solo el rollback de la transacción raíz descarta; el de un savepoint no.
    if previous_transaction.parent is None:
        session.info[_PENDIENTES] = []
