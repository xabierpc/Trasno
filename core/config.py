"""Configuración de Trasno: implementa `core.contracts.Settings` con pydantic-settings."""

from __future__ import annotations

from datetime import time
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración leída de variables TRASNO_*, luego de `.env`, luego de los defaults."""

    model_config = SettingsConfigDict(
        env_prefix="TRASNO_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    data_dir: Path = Path("data")
    user_id: int = 1
    ventana_madrugada: tuple[time, time] = (time(0, 0), time(6, 0))
    backup_dir: Path = Path("backups")
    backup_retencion_dias: int = 30
    timezone: str = "Europe/Madrid"
    scheduler_activo: bool = True  # False: la API no ejecuta trabajos programados
