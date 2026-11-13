"""Punto de entrada de la CLI `trasno` (migrate y backup llegan en tareas posteriores)."""

from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> int:
    """Ejecuta la CLI de Trasno."""
    parser = argparse.ArgumentParser(prog="trasno", description="Asistente personal Trasno.")
    parser.parse_args(argv)
    parser.print_help()
    return 0
