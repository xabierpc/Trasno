"""Casos de uso del briefing: generarlo a partir de las secciones de los módulos y enviarlo."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from core.contracts import SeccionBriefing
from modules.briefing.application.ports import Notificador
from modules.briefing.domain.briefing import Briefing, Seccion

logger = logging.getLogger(__name__)


def _ahora() -> datetime:
    return datetime.now(UTC)


class CasosUsoBriefing:
    """Genera el briefing pidiendo a cada módulo su sección.

    `secciones` es una función porque los módulos se registran después que el briefing
    (orden alfabético): se consulta en cada uso, igual que `series_providers`.
    """

    def __init__(
        self,
        secciones: Callable[[], list[SeccionBriefing]],
        zona: str,
        notificador: Notificador,
        reloj: Callable[[], datetime] = _ahora,
    ) -> None:
        self._secciones = secciones
        self._zona = ZoneInfo(zona)
        self._notificador = notificador
        self._reloj = reloj

    def briefing(self, dia: date | None = None) -> Briefing:
        """Briefing de `dia` (por defecto, hoy). Una sección que falla no impide el resto."""
        ahora = self._reloj().astimezone(self._zona)
        dia = dia or ahora.date()
        secciones = []
        for seccion in sorted(self._secciones(), key=lambda s: s.orden):
            try:
                lineas = seccion.lineas(dia)
            except Exception:
                logger.exception("La sección %r del briefing ha fallado", seccion.titulo)
                lineas = ["_(no se ha podido generar)_"]
            if lineas:
                secciones.append(Seccion(titulo=seccion.titulo, lineas=lineas))
        return Briefing(dia=dia, generado_en=ahora, secciones=secciones)

    def enviar_briefing(self) -> Briefing:
        """Genera el briefing de hoy y lo manda por el notificador (lo usa el trabajo diario)."""
        briefing = self.briefing()
        self._notificador.notificar("Trasno · briefing", _texto_plano(briefing))
        return briefing


def _texto_plano(briefing: Briefing) -> str:
    """Versión sin Markdown para una notificación: saludo y un renglón por línea."""
    renglones = [briefing.saludo]
    for seccion in briefing.secciones:
        renglones.append(f"{seccion.titulo}:")
        renglones += [f"  • {linea.replace('**', '').replace('_', '')}" for linea in seccion.lineas]
    return "\n".join(renglones)
