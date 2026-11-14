"""Copias de seguridad de los .sqlite con la API de backup de SQLite (segura con la app abierta)."""

from __future__ import annotations

import shutil
import sqlite3
from contextlib import closing
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from core.config import Settings as SettingsPorDefecto
from core.contracts import Settings


@dataclass(frozen=True)
class ResultadoBackup:
    """Qué hizo un backup: carpeta del día, ficheros copiados y carpetas antiguas borradas."""

    destino: Path
    copiados: list[str] = field(default_factory=list)
    borrados: list[Path] = field(default_factory=list)


def hacer_backup(settings: Settings | None = None, hoy: date | None = None) -> ResultadoBackup:
    """Copia cada `data_dir/*.sqlite` a `backup_dir/AAAA-MM-DD/` y aplica la retención."""
    settings = settings or SettingsPorDefecto()
    hoy = hoy or datetime.now(ZoneInfo(settings.timezone)).date()
    destino = settings.backup_dir / hoy.isoformat()
    destino.mkdir(parents=True, exist_ok=True)

    copiados = []
    for origen in sorted(settings.data_dir.glob("*.sqlite")):
        _copiar(origen, destino / origen.name)
        copiados.append(origen.name)

    borrados = _aplicar_retencion(settings.backup_dir, settings.backup_retencion_dias, hoy)
    return ResultadoBackup(destino=destino, copiados=copiados, borrados=borrados)


def restaurar(carpeta: Path, settings: Settings | None = None) -> list[str]:
    """Vuelca cada .sqlite de `carpeta` sobre su homónimo en `data_dir` y los devuelve."""
    settings = settings or SettingsPorDefecto()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    restaurados = []
    for copia in sorted(carpeta.glob("*.sqlite")):
        _copiar(copia, settings.data_dir / copia.name)
        restaurados.append(copia.name)
    return restaurados


def _copiar(origen: Path, destino: Path) -> None:
    """Copia consistente con `Connection.backup`: incluye lo que aún esté en el -wal."""
    with closing(sqlite3.connect(origen)) as src, closing(sqlite3.connect(destino)) as dst:
        src.backup(dst)


def _aplicar_retencion(backup_dir: Path, dias: int, hoy: date) -> list[Path]:
    """Borra las carpetas AAAA-MM-DD de hace más de `dias`; ignora cualquier otra carpeta."""
    borrados = []
    for carpeta in sorted(backup_dir.iterdir()):
        fecha = _fecha_de(carpeta)
        if fecha is not None and (hoy - fecha).days > dias:
            shutil.rmtree(carpeta)
            borrados.append(carpeta)
    return borrados


def _fecha_de(carpeta: Path) -> date | None:
    if not carpeta.is_dir():
        return None
    try:
        return date.fromisoformat(carpeta.name)
    except ValueError:
        return None
