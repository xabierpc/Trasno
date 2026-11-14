"""Arranca la API de Trasno en 127.0.0.1:8000."""

from __future__ import annotations

import logging

import uvicorn

from interfaces.api.app import create_app

# Fijo en el código: la API nunca escucha fuera de localhost (regla 10 de CLAUDE.md).
HOST = "127.0.0.1"
PORT = 8000


def main() -> None:
    """Configura el logging y sirve la API con uvicorn."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    uvicorn.run(create_app(), host=HOST, port=PORT)


if __name__ == "__main__":
    main()
