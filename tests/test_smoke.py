from __future__ import annotations

import core.contracts  # noqa: F401  (los contratos se importan sin errores)
from core.cli import main


def test_cli_arranca() -> None:
    assert main([]) == 0
