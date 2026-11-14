from __future__ import annotations

from datetime import date

import pytest

from core.bus import InMemoryEventBus
from core.config import Settings
from core.context import ContextoApp
from core.contracts import Tool
from core.herramientas import HerramientaInvalida, validar


class Casos:
    def larga(self) -> None:
        """Primera línea
        que sigue aquí.

        Esto ya no."""

    def crear_tarea(self, titulo: str, fecha: date | None = None) -> str:
        """Crea una tarea pendiente.

        Más detalles que el LLM no necesita.
        """
        return titulo

    def sin_docstring(self, titulo: str) -> str:
        return titulo

    def sin_tipos(self, titulo) -> str:
        """Le falta el tipo."""
        return titulo


CASOS = Casos()


def contexto() -> ContextoApp:
    return ContextoApp(
        bus=InMemoryEventBus(),
        engine_factory=lambda _n: None,  # type: ignore[arg-type,return-value]
        settings=Settings(_env_file=None),
    )


def test_la_descripcion_es_el_primer_parrafo_del_docstring():
    tool = validar(Tool(nombre="crear_tarea", funcion=CASOS.crear_tarea))
    assert tool.descripcion == "Crea una tarea pendiente."


def test_un_parrafo_de_varias_lineas_se_junta():
    assert validar(Tool(nombre="larga", funcion=CASOS.larga)).descripcion == (
        "Primera línea que sigue aquí."
    )


def test_una_descripcion_propia_se_respeta():
    tool = validar(Tool(nombre="crear_tarea", funcion=CASOS.crear_tarea, descripcion="Otra."))
    assert tool.descripcion == "Otra."


@pytest.mark.parametrize(
    "nombre", ["", "CrearTarea", "crear-tarea", "1tarea", "a" * 65, "planning.x"]
)
def test_nombres_no_validos(nombre: str):
    with pytest.raises(HerramientaInvalida, match="Nombre"):
        validar(Tool(nombre=nombre, funcion=CASOS.crear_tarea))


def test_sin_docstring_falla():
    with pytest.raises(HerramientaInvalida, match="docstring"):
        validar(Tool(nombre="x", funcion=CASOS.sin_docstring))


def test_parametros_sin_tipo_fallan():
    with pytest.raises(HerramientaInvalida, match="sin tipo: titulo"):
        validar(Tool(nombre="x", funcion=CASOS.sin_tipos))


def test_el_contexto_valida_y_no_admite_repetidas():
    ctx = contexto()
    ctx.add_tool(Tool(nombre="crear_tarea", funcion=CASOS.crear_tarea, requiere_confirmacion=True))
    ctx.add_tool(Tool(nombre="borrar_tarea", funcion=CASOS.crear_tarea, sensible=True))

    assert [t.nombre for t in ctx.tools()] == ["borrar_tarea", "crear_tarea"]
    assert ctx.tools()[1].descripcion == "Crea una tarea pendiente."
    with pytest.raises(HerramientaInvalida, match="dos herramientas"):
        ctx.add_tool(Tool(nombre="crear_tarea", funcion=CASOS.crear_tarea))
    with pytest.raises(HerramientaInvalida):
        ctx.add_tool(Tool(nombre="otra", funcion=CASOS.sin_docstring))
