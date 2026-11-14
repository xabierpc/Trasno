from __future__ import annotations

from datetime import time
from pathlib import Path

import pytest

from core.config import Settings


def test_carga_valores_por_defecto() -> None:
    settings = Settings(_env_file=None)

    assert settings.data_dir == Path("data")
    assert settings.user_id == 1
    assert settings.ventana_madrugada == (time(0, 0), time(6, 0))
    assert settings.backup_dir == Path("backups")
    assert settings.backup_retencion_dias == 30
    assert settings.timezone == "Europe/Madrid"


def test_variable_de_entorno_sobrescribe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRASNO_DATA_DIR", "/tmp/trasno")
    monkeypatch.setenv("TRASNO_BACKUP_RETENCION_DIAS", "7")
    monkeypatch.setenv("TRASNO_VENTANA_MADRUGADA", '["01:00", "05:30"]')

    settings = Settings(_env_file=None)

    assert settings.data_dir == Path("/tmp/trasno")
    assert settings.backup_retencion_dias == 7
    assert settings.ventana_madrugada == (time(1, 0), time(5, 30))


def test_lee_fichero_env(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text("TRASNO_TIMEZONE=Europe/London\n", encoding="utf-8")

    settings = Settings(_env_file=env)

    assert settings.timezone == "Europe/London"


def test_entorno_gana_al_fichero_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env = tmp_path / ".env"
    env.write_text("TRASNO_USER_ID=2\n", encoding="utf-8")
    monkeypatch.setenv("TRASNO_USER_ID", "3")

    settings = Settings(_env_file=env)

    assert settings.user_id == 3
