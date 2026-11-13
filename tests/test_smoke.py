from __future__ import annotations

from datetime import time

from core.cli import main
from core.contracts import Settings


def test_settings_por_defecto() -> None:
    settings = Settings()
    assert settings.timezone == "Europe/Madrid"
    assert settings.ventana_madrugada == (time(0, 0), time(6, 0))


def test_cli_arranca() -> None:
    assert main([]) == 0
