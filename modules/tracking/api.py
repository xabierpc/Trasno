"""Router FastAPI de tracking: traduce HTTP ↔ casos de uso, sin lógica de negocio."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from datetime import UTC, date, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.routing import APIRoute
from pydantic import BaseModel, StrictBool, StrictFloat, StrictInt, StrictStr

from core.contracts import Settings
from modules.tracking.application.casos_uso import CasosUsoTracking
from modules.tracking.domain.errores import (
    EntradaNoEncontrada,
    ErrorTracking,
    MetricaDuplicada,
    MetricaNoEncontrada,
)
from modules.tracking.domain.fecha_logica import es_madrugada, opciones_fecha_logica
from modules.tracking.domain.metricas import (
    Agregacion,
    MetricDefinition,
    MetricEntry,
    PoliticaDuplicado,
    TipoMetrica,
)

Valor = StrictBool | StrictInt | StrictFloat | StrictStr


class MetricaEntrada(BaseModel):
    """Cuerpo de POST /tracking/metrics."""

    nombre: str
    unidad: str = ""
    tipo: TipoMetrica
    agregacion: Agregacion = Agregacion.ULTIMA
    on_duplicate: PoliticaDuplicado = PoliticaDuplicado.REPLACE
    objetivo: float | None = None
    minimo: float | None = None
    maximo: float | None = None
    escala_max: int | None = None
    categorias: list[str] = []


class MetricaSalida(MetricaEntrada):
    """Una métrica tal como la devuelve la API."""

    id: str


class RegistroEntrada(BaseModel):
    """Cuerpo de POST /tracking/entries; `logical_date` es obligatoria (regla 5)."""

    metric: str
    valor: Valor
    logical_date: date
    timestamp: datetime | None = None


class RegistroSalida(BaseModel):
    """Una entrada tal como la devuelve la API."""

    id: str
    metric: str
    valor: Valor
    timestamp: datetime
    logical_date: date
    slot: int


class FechaLogica(BaseModel):
    """Lo que necesita un cliente para saber si debe preguntar «¿ayer u hoy?»."""

    es_madrugada: bool
    ayer: date
    hoy: date


_ESTADOS: dict[type[ErrorTracking], int] = {
    MetricaNoEncontrada: status.HTTP_404_NOT_FOUND,
    EntradaNoEncontrada: status.HTTP_404_NOT_FOUND,
    MetricaDuplicada: status.HTTP_409_CONFLICT,
}


class _RutaTracking(APIRoute):
    """Convierte los errores de dominio en respuestas HTTP: 404, 409 o 422 (el resto)."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        original = super().get_route_handler()

        async def manejar(request: Request) -> Response:
            try:
                return await original(request)
            except ErrorTracking as error:
                estado = _ESTADOS.get(type(error), status.HTTP_422_UNPROCESSABLE_CONTENT)
                raise HTTPException(status_code=estado, detail=str(error)) from error

        return manejar


def _ahora() -> datetime:
    return datetime.now(UTC)


def crear_router(
    casos: CasosUsoTracking,
    settings: Settings,
    reloj: Callable[[], datetime] = _ahora,
) -> APIRouter:
    """Crea el router /tracking sobre los casos de uso recibidos."""
    router = APIRouter(prefix="/tracking", tags=["tracking"], route_class=_RutaTracking)

    @router.post("/metrics", status_code=status.HTTP_201_CREATED)
    def crear_metrica(datos: MetricaEntrada) -> MetricaSalida:
        """Crea una métrica nueva."""
        campos = datos.model_dump()
        campos["categorias"] = tuple(datos.categorias)
        return _metrica(casos.crear_metrica(**campos))

    @router.get("/metrics")
    def listar_metricas() -> list[MetricaSalida]:
        """Lista las métricas definidas."""
        return [_metrica(m) for m in casos.listar_metricas()]

    @router.post("/entries", status_code=status.HTTP_201_CREATED)
    def registrar(datos: RegistroEntrada) -> RegistroSalida:
        """Guarda un valor; si la métrica es `replace`, sobrescribe el del mismo día."""
        entrada = casos.registrar_metrica(
            datos.metric, datos.valor, datos.logical_date, datos.timestamp
        )
        return _registro(entrada, datos.metric)

    @router.get("/entries")
    def listar_entradas(
        metric: str, desde: date = date.min, hasta: date = date.max
    ) -> list[RegistroSalida]:
        """Entradas de una métrica entre `desde` y `hasta` (ambos incluidos)."""
        return [_registro(e, metric) for e in casos.listar_entradas(metric, desde, hasta)]

    @router.delete("/entries/{entrada_id}", status_code=status.HTTP_204_NO_CONTENT)
    def borrar_entrada(entrada_id: str) -> None:
        """Borra una entrada (borrado real)."""
        casos.borrar_entrada(entrada_id)

    @router.get("/fecha-logica")
    def fecha_logica() -> FechaLogica:
        """Indica si ahora es madrugada y qué dos fechas ofrecer al usuario."""
        ahora = reloj()
        ayer, hoy = opciones_fecha_logica(ahora, settings.timezone)
        madrugada = es_madrugada(ahora, settings.ventana_madrugada, settings.timezone)
        return FechaLogica(es_madrugada=madrugada, ayer=ayer, hoy=hoy)

    return router


def _metrica(definicion: MetricDefinition) -> MetricaSalida:
    return MetricaSalida(
        id=definicion.id,
        nombre=definicion.nombre,
        unidad=definicion.unidad,
        tipo=definicion.tipo,
        agregacion=definicion.agregacion,
        on_duplicate=definicion.on_duplicate,
        objetivo=definicion.objetivo,
        minimo=definicion.minimo,
        maximo=definicion.maximo,
        escala_max=definicion.escala_max,
        categorias=list(definicion.categorias),
    )


def _registro(entrada: MetricEntry, metrica: str) -> RegistroSalida:
    return RegistroSalida(
        id=entrada.id,
        metric=metrica,
        valor=entrada.valor,
        timestamp=entrada.timestamp,
        logical_date=entrada.logical_date,
        slot=entrada.slot,
    )
