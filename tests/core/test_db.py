from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text

from core.db import make_engine


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    directorio = tmp_path / "data"  # aún no existe: make_engine debe crearlo
    monkeypatch.setenv("TRASNO_DATA_DIR", str(directorio))
    return directorio


def test_crea_data_dir_y_fichero_del_modulo(data_dir: Path) -> None:
    engine = make_engine("tracking")
    with engine.connect():
        pass
    engine.dispose()

    assert (data_dir / "tracking.sqlite").is_file()


def test_conexion_nueva_activa_foreign_keys_y_wal(data_dir: Path) -> None:
    engine = make_engine("tracking")

    with engine.connect() as conn:
        foreign_keys = conn.execute(text("PRAGMA foreign_keys")).scalar_one()
        journal_mode = conn.execute(text("PRAGMA journal_mode")).scalar_one()
    engine.dispose()

    assert foreign_keys == 1
    assert journal_mode == "wal"
