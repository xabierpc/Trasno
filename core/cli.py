"""Punto de entrada de la CLI `trasno`."""

from __future__ import annotations

import argparse
import logging

from core.migraciones import migrar_todo


def main(argv: list[str] | None = None) -> int:
    """Ejecuta la CLI de Trasno."""
    parser = argparse.ArgumentParser(prog="trasno", description="Asistente personal Trasno.")
    subcomandos = parser.add_subparsers(dest="comando")
    subcomandos.add_parser("migrate", help="aplica las migraciones de core y de cada módulo")
    args = parser.parse_args(argv)

    if args.comando == "migrate":
        return _migrate()
    parser.print_help()
    return 0


def _migrate() -> int:
    """Migra todas las bases de datos y muestra cuáles se han tocado."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    migrados = migrar_todo()
    print(f"Migrados: {', '.join(migrados)}")
    return 0
