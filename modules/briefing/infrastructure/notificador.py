"""Notificadores del briefing: escritorio (notify-send en Linux) o solo el log."""

from __future__ import annotations

import logging
import shutil
import subprocess

logger = logging.getLogger(__name__)


class NotificadorLog:
    """Deja el aviso en el log. Sirve donde no hay escritorio (y como respaldo)."""

    def notificar(self, titulo: str, texto: str) -> None:
        logger.info("%s\n%s", titulo, texto)


class NotificadorEscritorio:
    """Notificación del sistema con `notify-send` (Linux). Si no existe, usa el log."""

    def __init__(self, programa: str = "notify-send") -> None:
        self._ruta = shutil.which(programa)
        self._respaldo = NotificadorLog()

    def notificar(self, titulo: str, texto: str) -> None:
        self._respaldo.notificar(titulo, texto)
        if self._ruta is None:
            return
        try:
            subprocess.run(  # argumentos fijos y sin shell: el texto no se interpreta
                [self._ruta, "--app-name=Trasno", "--expire-time=60000", titulo, texto],
                check=True,
                timeout=5,
                capture_output=True,
            )
        except (OSError, subprocess.SubprocessError):
            logger.warning("No se pudo mostrar la notificación de escritorio", exc_info=True)
