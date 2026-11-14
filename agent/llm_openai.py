"""Adaptador LLM para cualquier API compatible con OpenAI: Ollama (/v1), Groq, OpenRouter…

Usa `httpx` (ya está en las dependencias) en lugar del SDK de cada proveedor: cambiar de
proveedor es cambiar `TRASNO_LLM_URL` y `TRASNO_LLM_MODELO`.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from typing import Any

import httpx
import keyring
from keyring.errors import KeyringError

from agent.mensajes import ErrorLLM, LlamadaHerramienta, Mensaje, RespuestaLLM, Rol

logger = logging.getLogger(__name__)

SERVICIO_KEYRING, USUARIO_KEYRING = "trasno", "llm"
TIMEOUT_SEGUNDOS = 120.0  # un modelo local en CPU puede tardar
_PENSAMIENTO = re.compile(r"<think>.*?</think>", re.DOTALL)


def clave_de_keyring() -> str | None:
    """Clave de la API guardada con `keyring set trasno llm`, o None si no hay (Ollama)."""
    try:
        return keyring.get_password(SERVICIO_KEYRING, USUARIO_KEYRING)
    except KeyringError:
        return None


class LLMOpenAICompatible:
    """Implementa el port `LLM` sobre `POST {url}/chat/completions`."""

    def __init__(
        self,
        url: str,
        modelo: str,
        clave: Callable[[], str | None] = clave_de_keyring,
        cliente: httpx.Client | None = None,
    ) -> None:
        self._url = url.rstrip("/")
        self._modelo = modelo
        self._clave = clave
        self._cliente = cliente or httpx.Client(timeout=TIMEOUT_SEGUNDOS)

    def responder(
        self, mensajes: list[Mensaje], herramientas: list[dict[str, Any]]
    ) -> RespuestaLLM:
        cuerpo: dict[str, Any] = {
            "model": self._modelo,
            "messages": [_a_openai(m) for m in mensajes],
            "temperature": 0.2,
        }
        if herramientas:
            cuerpo["tools"] = herramientas
        cabeceras = {}
        if clave := self._clave():
            cabeceras["Authorization"] = f"Bearer {clave}"
        try:
            respuesta = self._cliente.post(
                f"{self._url}/chat/completions", json=cuerpo, headers=cabeceras
            )
        except httpx.HTTPError as error:
            raise ErrorLLM(f"No se puede contactar con el LLM en {self._url}: {error}") from error
        if not respuesta.is_success:
            raise ErrorLLM(f"El LLM ha respondido {respuesta.status_code}: {respuesta.text[:300]}")
        try:
            mensaje = respuesta.json()["choices"][0]["message"]
        except (ValueError, KeyError, IndexError) as error:
            raise ErrorLLM(f"Respuesta del LLM inesperada: {respuesta.text[:300]}") from error
        return RespuestaLLM(
            texto=_PENSAMIENTO.sub("", mensaje.get("content") or "").strip(),
            llamadas=[_llamada(ll) for ll in mensaje.get("tool_calls") or []],
        )


def _a_openai(mensaje: Mensaje) -> dict[str, Any]:
    datos: dict[str, Any] = {"role": mensaje.rol.value, "content": mensaje.contenido}
    if mensaje.rol is Rol.HERRAMIENTA:
        datos["tool_call_id"] = mensaje.llamada_id
    if mensaje.llamadas:
        datos["tool_calls"] = [
            {
                "id": ll.id,
                "type": "function",
                "function": {
                    "name": ll.nombre,
                    "arguments": json.dumps(ll.argumentos, ensure_ascii=False),
                },
            }
            for ll in mensaje.llamadas
        ]
    return datos


def _llamada(datos: dict[str, Any]) -> LlamadaHerramienta:
    funcion = datos.get("function", {})
    crudos = funcion.get("arguments") or "{}"
    try:
        argumentos = json.loads(crudos) if isinstance(crudos, str) else dict(crudos)
    except ValueError:
        # Se pasa tal cual: la validación de argumentos devolverá el error al LLM para que corrija.
        argumentos = {"_json_no_valido": crudos}
    if not isinstance(argumentos, dict):
        argumentos = {"_json_no_valido": crudos}
    return LlamadaHerramienta(
        id=str(datos.get("id") or funcion.get("name", "")),
        nombre=str(funcion.get("name", "")),
        argumentos=argumentos,
    )
