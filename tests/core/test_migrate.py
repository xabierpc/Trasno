from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from core.cli import main
from core.migraciones import migrar_todo

PAQUETE = "modulos_migrate_prueba"

ENV_PY = """
from sqlalchemy import MetaData

from core.migraciones import ejecutar_env

ejecutar_env(MetaData(), "prueba")
"""

REVISION = '''
"""Tabla de prueba."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "nota",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("texto", sa.String(100), nullable=False),
    )


def downgrade():
    op.drop_table("nota")
'''

ARRANQUE = """
from sqlalchemy import text


def datos_arranque(engine):
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO nota VALUES (1, 1, 'hola') ON CONFLICT DO NOTHING")
        )
"""


def _escribir(ruta: Path, contenido: str = "") -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(contenido, encoding="utf-8")


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    directorio = tmp_path / "data"
    monkeypatch.setenv("TRASNO_DATA_DIR", str(directorio))
    return directorio


@pytest.fixture
def paquete_prueba(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """`prueba` tiene migraciones y datos de arranque; `sin_bd` no tiene base de datos."""
    raiz = tmp_path / "paquetes" / PAQUETE
    _escribir(raiz / "__init__.py")
    infra = raiz / "prueba" / "infrastructure"
    _escribir(raiz / "prueba" / "__init__.py")
    _escribir(infra / "__init__.py")
    _escribir(infra / "migrations" / "env.py", ENV_PY)
    _escribir(infra / "migrations" / "versions" / "0001_nota.py", REVISION)
    _escribir(infra / "arranque.py", ARRANQUE)
    _escribir(raiz / "sin_bd" / "__init__.py")
    monkeypatch.syspath_prepend(str(tmp_path / "paquetes"))
    yield PAQUETE
    for nombre in [n for n in sys.modules if n.split(".")[0] == PAQUETE]:
        del sys.modules[nombre]


def _contar(sqlite: Path, tabla: str) -> int:
    engine = create_engine(f"sqlite:///{sqlite}")
    try:
        with engine.connect() as conn:
            return conn.execute(text(f'SELECT count(*) FROM "{tabla}"')).scalar_one()
    finally:
        engine.dispose()


def test_migra_core_y_modulos_y_ejecuta_datos_de_arranque(
    data_dir: Path, paquete_prueba: str
) -> None:
    migrados = migrar_todo(paquete_modulos=paquete_prueba)

    assert migrados == ["core", "prueba"]
    assert _contar(data_dir / "core.sqlite", "user") == 1
    assert _contar(data_dir / "prueba.sqlite", "nota") == 1
    assert not (data_dir / "sin_bd.sqlite").exists()


def test_migrar_dos_veces_no_duplica_nada(data_dir: Path, paquete_prueba: str) -> None:
    migrar_todo(paquete_modulos=paquete_prueba)
    migrar_todo(paquete_modulos=paquete_prueba)

    assert _contar(data_dir / "core.sqlite", "user") == 1
    assert _contar(data_dir / "prueba.sqlite", "nota") == 1


def test_comando_migrate(data_dir: Path) -> None:
    assert main(["migrate"]) == 0
    assert _contar(data_dir / "core.sqlite", "user") == 1
