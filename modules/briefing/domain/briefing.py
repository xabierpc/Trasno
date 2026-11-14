"""El briefing del día: un saludo y las secciones que aportan los módulos, en Markdown."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

DIAS_SEMANA = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")


@dataclass(frozen=True)
class Seccion:
    """Una parte del briefing ya generada."""

    titulo: str
    lineas: list[str]


@dataclass(frozen=True)
class Briefing:
    """Resumen de un día. No se guarda: se genera cada vez que se pide."""

    dia: date
    generado_en: datetime
    secciones: list[Seccion]

    @property
    def saludo(self) -> str:
        hora = self.generado_en.hour
        if 6 <= hora < 14:
            saludo = "Buenos días"
        elif 14 <= hora < 21:
            saludo = "Buenas tardes"
        else:
            saludo = "Buenas noches"
        return f"{saludo}. Hoy es {DIAS_SEMANA[self.dia.weekday()]} {self.dia:%d/%m}."

    def markdown(self) -> str:
        """El briefing completo: saludo y una lista por sección."""
        partes = [self.saludo]
        for seccion in self.secciones:
            lista = "\n".join(f"- {linea}" for linea in seccion.lineas)
            partes.append(f"**{seccion.titulo}**\n{lista}")
        if not self.secciones:
            partes.append("Nada que contar por ahora.")
        return "\n\n".join(partes)
