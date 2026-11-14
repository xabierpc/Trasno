from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime, time
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine

import core
from agent.agente import Agente
from agent.mensajes import LlamadaHerramienta, Mensaje, RespuestaLLM
from core.acciones import RegistroAccionesSQL
from core.contracts import Tool
from core.db import make_engine

ALEMBIC_INI = Path(core.__file__).parent / "migrations" / "alembic.ini"
# Lunes 16/11/2026 a las 10:00 en Madrid
AHORA = datetime(2026, 11, 16, 9, 0, tzinfo=UTC)
VENTANA = (time(0), time(6))


class LLMGuion:
    """LLM falso: devuelve las respuestas del guion en orden y guarda lo que recibe."""

    def __init__(self, *respuestas: RespuestaLLM) -> None:
        self._respuestas = list(respuestas)
        self.recibidos: list[list[Mensaje]] = []
        self.herramientas: list[list[dict[str, Any]]] = []

    def responder(
        self, mensajes: list[Mensaje], herramientas: list[dict[str, Any]]
    ) -> RespuestaLLM:
        self.recibidos.append(list(mensajes))
        self.herramientas.append(herramientas)
        return self._respuestas.pop(0)


def llamada(herramienta: str, /, id_llamada: str = "c1", **argumentos: Any) -> LlamadaHerramienta:
    """Atajo: llamada("agenda", dia="2026-11-16") es el LLM pidiendo esa herramienta."""
    return LlamadaHerramienta(id=id_llamada, nombre=herramienta, argumentos=argumentos)


def pide(*llamadas: LlamadaHerramienta) -> RespuestaLLM:
    return RespuestaLLM(llamadas=list(llamadas))


def dice(texto: str) -> RespuestaLLM:
    return RespuestaLLM(texto=texto)


class Agenda:
    """Casos de uso falsos para probar el agente sin módulos reales."""

    def __init__(self) -> None:
        self.tareas: list[tuple[str, date | None]] = []

    def crear_tarea(self, titulo: str, fecha: date | None = None) -> str:
        """Crea una tarea."""
        self.tareas.append((titulo, fecha))
        return f"Tarea creada: {titulo}"

    def registrar_peso(self, kg: float, fecha: date) -> str:
        """Guarda el peso."""
        return f"Peso {kg} el {fecha}"

    def rompe(self) -> str:
        """Siempre falla."""
        raise RuntimeError("boom")


@pytest.fixture
def engine_core(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    monkeypatch.setenv("TRASNO_DATA_DIR", str(tmp_path))
    command.upgrade(Config(str(ALEMBIC_INI)), "head")
    engine = make_engine("core")
    yield engine
    engine.dispose()


@pytest.fixture
def acciones(engine_core: Engine) -> RegistroAccionesSQL:
    return RegistroAccionesSQL(engine_core, 1)


@pytest.fixture
def agenda() -> Agenda:
    return Agenda()


@pytest.fixture
def herramientas(agenda: Agenda) -> list[Tool]:
    return [
        Tool(nombre="crear_tarea", funcion=agenda.crear_tarea, requiere_confirmacion=True),
        Tool(nombre="registrar_peso", funcion=agenda.registrar_peso),
        Tool(nombre="rompe", funcion=agenda.rompe),
    ]


def crear_agente(llm: LLMGuion, herramientas: list[Tool], acciones: RegistroAccionesSQL) -> Agente:
    return Agente(
        llm,
        herramientas=lambda: herramientas,
        acciones=lambda: acciones,
        zona="Europe/Madrid",
        ventana_madrugada=VENTANA,
        reloj=lambda: AHORA,
    )
