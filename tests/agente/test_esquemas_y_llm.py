from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Any

import httpx
import pytest
from pydantic import ValidationError

from agent.esquemas import argumentos, esquema_openai
from agent.llm_openai import LLMOpenAICompatible
from agent.mensajes import ErrorLLM, LlamadaHerramienta, Mensaje, Rol
from core.contracts import Tool
from core.herramientas import validar


class Color(StrEnum):
    """Docstring para programadores."""

    ROJO = "rojo"
    AZUL = "azul"


@dataclass
class Pieza:
    nombre: str
    cantidad: int = 1


def ejemplo(dia: date, color: Color = Color.ROJO, piezas: list[Pieza] | None = None) -> str:
    """Hace algo de ejemplo."""
    return f"{dia} {color} {piezas}"


TOOL = validar(Tool(nombre="ejemplo", funcion=ejemplo))


# --- Esquemas -------------------------------------------------------------------------------


def test_esquema_openai_sin_referencias_ni_titulos():
    esquema = esquema_openai(TOOL)
    assert esquema["function"]["name"] == "ejemplo"
    assert esquema["function"]["description"] == "Hace algo de ejemplo."
    parametros = esquema["function"]["parameters"]
    texto = json.dumps(parametros)
    assert "$ref" not in texto and "$defs" not in texto and '"title"' not in texto
    assert "programadores" not in texto
    assert parametros["required"] == ["dia"]
    assert parametros["properties"]["color"]["enum"] == ["rojo", "azul"]
    pieza = parametros["properties"]["piezas"]["anyOf"][0]["items"]
    assert set(pieza["properties"]) == {"nombre", "cantidad"}


def test_argumentos_se_convierten_a_los_tipos_de_la_funcion():
    kwargs = argumentos(TOOL, {"dia": "2026-11-16", "color": "azul", "piezas": [{"nombre": "x"}]})
    assert kwargs == {"dia": date(2026, 11, 16), "color": Color.AZUL, "piezas": [Pieza("x", 1)]}
    assert ejemplo(**kwargs).startswith("2026-11-16 azul")


@pytest.mark.parametrize(
    "datos",
    [
        {},
        {"dia": "ayer"},
        {"dia": "2026-11-16", "color": "verde"},
        {"dia": "2026-11-16", "otro": 1},
    ],
)
def test_argumentos_no_validos(datos: dict[str, Any]):
    with pytest.raises(ValidationError):
        argumentos(TOOL, datos)


# --- Adaptador OpenAI -----------------------------------------------------------------------


def llm_con(respuesta: httpx.Response, peticiones: list[httpx.Request], clave: str | None = "k"):
    def manejar(peticion: httpx.Request) -> httpx.Response:
        peticiones.append(peticion)
        return respuesta

    cliente = httpx.Client(transport=httpx.MockTransport(manejar))
    return LLMOpenAICompatible("http://llm/v1/", "modelo", clave=lambda: clave, cliente=cliente)


def openai(mensaje: dict[str, Any]) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": mensaje}]})


def test_peticion_en_formato_openai():
    peticiones: list[httpx.Request] = []
    llm = llm_con(openai({"content": "hola"}), peticiones)
    conversacion = [
        Mensaje(rol=Rol.SISTEMA, contenido="s"),
        Mensaje(
            rol=Rol.ASISTENTE,
            llamadas=(LlamadaHerramienta(id="c1", nombre="agenda", argumentos={"dia": "x"}),),
        ),
        Mensaje(rol=Rol.HERRAMIENTA, contenido="r", llamada_id="c1"),
    ]

    assert llm.responder(conversacion, [esquema_openai(TOOL)]).texto == "hola"

    (peticion,) = peticiones
    assert str(peticion.url) == "http://llm/v1/chat/completions"
    assert peticion.headers["Authorization"] == "Bearer k"
    cuerpo = json.loads(peticion.content)
    assert cuerpo["model"] == "modelo" and cuerpo["tools"][0]["function"]["name"] == "ejemplo"
    assert cuerpo["messages"][1]["tool_calls"][0]["function"] == {
        "name": "agenda",
        "arguments": '{"dia": "x"}',
    }
    assert cuerpo["messages"][2] == {"role": "tool", "content": "r", "tool_call_id": "c1"}


def test_sin_clave_no_manda_cabecera():
    peticiones: list[httpx.Request] = []
    llm_con(openai({"content": "x"}), peticiones, clave=None).responder([], [])
    assert "Authorization" not in peticiones[0].headers
    assert "tools" not in json.loads(peticiones[0].content)


def test_lee_las_llamadas_y_quita_el_pensamiento():
    respuesta = openai(
        {
            "content": "<think>razono…</think>Voy.",
            "tool_calls": [
                {"id": "a", "function": {"name": "agenda", "arguments": '{"dia": "2026-11-16"}'}},
                {"id": "b", "function": {"name": "agenda", "arguments": "{roto"}},
            ],
        }
    )
    resultado = llm_con(respuesta, []).responder([], [])

    assert resultado.texto == "Voy."
    assert resultado.llamadas == [
        LlamadaHerramienta(id="a", nombre="agenda", argumentos={"dia": "2026-11-16"}),
        LlamadaHerramienta(id="b", nombre="agenda", argumentos={"_json_no_valido": "{roto"}),
    ]


@pytest.mark.parametrize(
    "respuesta", [httpx.Response(500, text="caído"), httpx.Response(200, json={"raro": 1})]
)
def test_errores_del_llm(respuesta: httpx.Response):
    with pytest.raises(ErrorLLM):
        llm_con(respuesta, []).responder([], [])


def test_llm_inalcanzable():
    def falla(_peticion: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no hay nadie")

    cliente = httpx.Client(transport=httpx.MockTransport(falla))
    llm = LLMOpenAICompatible("http://llm/v1", "m", clave=lambda: None, cliente=cliente)
    with pytest.raises(ErrorLLM, match="No se puede contactar"):
        llm.responder([], [])
