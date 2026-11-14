"""Router FastAPI del briefing."""

from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter
from pydantic import BaseModel

from modules.briefing.application.casos_uso import CasosUsoBriefing


class SeccionSalida(BaseModel):
    titulo: str
    lineas: list[str]


class BriefingSalida(BaseModel):
    """El briefing estructurado y ya montado en Markdown."""

    dia: date
    generado_en: datetime
    saludo: str
    secciones: list[SeccionSalida]
    markdown: str


def crear_router(casos: CasosUsoBriefing) -> APIRouter:
    router = APIRouter(prefix="/briefing", tags=["briefing"])

    @router.get("")
    def briefing(dia: date | None = None) -> BriefingSalida:
        """Briefing de `dia` (por defecto, hoy), generado en el momento."""
        b = casos.briefing(dia)
        return BriefingSalida(
            dia=b.dia,
            generado_en=b.generado_en,
            saludo=b.saludo,
            secciones=[SeccionSalida(titulo=s.titulo, lineas=s.lineas) for s in b.secciones],
            markdown=b.markdown(),
        )

    return router
