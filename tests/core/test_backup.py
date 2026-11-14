from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import date
from pathlib import Path

import pytest

from core.backup import hacer_backup, restaurar
from core.cli import main
from core.config import Settings

HOY = date(2026, 11, 14)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    (tmp_path / "data").mkdir()
    return Settings(
        _env_file=None,
        data_dir=tmp_path / "data",
        backup_dir=tmp_path / "backups",
        backup_retencion_dias=10,
    )


def _filas(sqlite: Path) -> list[tuple[int, str]]:
    with closing(sqlite3.connect(sqlite)) as conn:
        return conn.execute("SELECT id, texto FROM nota ORDER BY id").fetchall()


def test_backup_y_restaurar_devuelve_los_mismos_datos(settings: Settings) -> None:
    original = [(1, "hola"), (2, "adiós")]
    db = settings.data_dir / "tracking.sqlite"
    # Conexión abierta en WAL: parte de los datos aún no está en el fichero principal.
    conn = sqlite3.connect(db)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE nota (id INTEGER PRIMARY KEY, texto TEXT)")
    conn.executemany("INSERT INTO nota VALUES (?, ?)", original)
    conn.commit()

    resultado = hacer_backup(settings, hoy=HOY)

    copia = settings.backup_dir / "2026-11-14" / "tracking.sqlite"
    assert resultado.destino == copia.parent
    assert resultado.copiados == ["tracking.sqlite"]
    assert _filas(copia) == original

    conn.execute("DELETE FROM nota")
    conn.execute("INSERT INTO nota VALUES (99, 'basura')")
    conn.commit()
    conn.close()

    restaurar(resultado.destino, settings)

    assert _filas(db) == original


def test_borra_backups_de_mas_de_la_retencion(settings: Settings) -> None:
    for nombre in ("2026-10-01", "2026-11-03", "2026-11-04", "notas"):
        (settings.backup_dir / nombre).mkdir(parents=True)

    resultado = hacer_backup(settings, hoy=HOY)

    restantes = sorted(p.name for p in settings.backup_dir.iterdir())
    assert restantes == ["2026-11-04", "2026-11-14", "notas"]  # 10 días se conserva, 11 no
    assert sorted(p.name for p in resultado.borrados) == ["2026-10-01", "2026-11-03"]


def test_comando_backup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "data").mkdir()
    sqlite3.connect(tmp_path / "data" / "core.sqlite").close()
    monkeypatch.setenv("TRASNO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("TRASNO_BACKUP_DIR", str(tmp_path / "backups"))

    assert main(["backup"]) == 0
    assert list((tmp_path / "backups").glob("*/core.sqlite"))
