from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from core.bus import InMemoryEventBus, publicar_tras_commit
from core.contracts import Event


@dataclass(frozen=True, kw_only=True)
class PesoRegistrado(Event):
    kilos: float


@dataclass(frozen=True, kw_only=True)
class EntrenoTerminado(Event):
    minutos: int


@pytest.fixture
def bus() -> InMemoryEventBus:
    return InMemoryEventBus()


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine("sqlite://")
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_solo_recibe_los_eventos_del_tipo_suscrito(bus: InMemoryEventBus) -> None:
    pesos: list[PesoRegistrado] = []
    bus.subscribe(PesoRegistrado, pesos.append)

    bus.publish(PesoRegistrado(kilos=72.5))
    bus.publish(EntrenoTerminado(minutos=45))

    assert pesos == [PesoRegistrado(kilos=72.5)]


def test_suscribirse_a_la_base_recibe_todos(bus: InMemoryEventBus) -> None:
    todos: list[Event] = []
    bus.subscribe(Event, todos.append)

    bus.publish(PesoRegistrado(kilos=72.5))
    bus.publish(EntrenoTerminado(minutos=45))

    assert todos == [PesoRegistrado(kilos=72.5), EntrenoTerminado(minutos=45)]


def test_handlers_en_orden_de_suscripcion(bus: InMemoryEventBus) -> None:
    llamadas: list[str] = []
    bus.subscribe(PesoRegistrado, lambda _: llamadas.append("primero"))
    bus.subscribe(Event, lambda _: llamadas.append("segundo"))
    bus.subscribe(PesoRegistrado, lambda _: llamadas.append("tercero"))

    bus.publish(PesoRegistrado(kilos=72.5))

    assert llamadas == ["primero", "segundo", "tercero"]


def test_excepcion_en_un_handler_queda_aislada(
    bus: InMemoryEventBus, caplog: pytest.LogCaptureFixture
) -> None:
    recibidos: list[PesoRegistrado] = []

    def roto(_: PesoRegistrado) -> None:
        raise RuntimeError("fallo del handler")

    bus.subscribe(PesoRegistrado, roto)
    bus.subscribe(PesoRegistrado, recibidos.append)

    with caplog.at_level(logging.ERROR, logger="core.bus"):
        bus.publish(PesoRegistrado(kilos=72.5))  # no debe lanzar

    assert recibidos == [PesoRegistrado(kilos=72.5)]
    assert "fallo del handler" in caplog.text


def test_publica_solo_tras_el_commit(bus: InMemoryEventBus, session: Session) -> None:
    recibidos: list[Event] = []
    bus.subscribe(Event, recibidos.append)

    publicar_tras_commit(session, bus, PesoRegistrado(kilos=72.5))
    publicar_tras_commit(session, bus, EntrenoTerminado(minutos=45))
    assert recibidos == []

    session.commit()

    assert recibidos == [PesoRegistrado(kilos=72.5), EntrenoTerminado(minutos=45)]


def test_no_publica_si_hay_rollback(bus: InMemoryEventBus, session: Session) -> None:
    recibidos: list[Event] = []
    bus.subscribe(Event, recibidos.append)

    publicar_tras_commit(session, bus, PesoRegistrado(kilos=72.5))
    session.rollback()
    session.commit()  # un commit posterior no resucita eventos descartados

    assert recibidos == []


def test_no_publica_dos_veces_en_commits_sucesivos(bus: InMemoryEventBus, session: Session) -> None:
    recibidos: list[Event] = []
    bus.subscribe(Event, recibidos.append)

    publicar_tras_commit(session, bus, PesoRegistrado(kilos=72.5))
    session.commit()
    session.commit()

    assert recibidos == [PesoRegistrado(kilos=72.5)]
