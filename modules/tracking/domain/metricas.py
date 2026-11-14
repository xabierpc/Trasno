"""Métricas genéricas: definición configurable y entradas diarias.

Representación de los valores por tipo (es lo que devuelve `MetricDefinition.validar`):

| Tipo       | Python  | Nota                                   |
|------------|---------|----------------------------------------|
| numérica   | `float` | rango opcional `minimo`/`maximo`       |
| duración   | `int`   | minutos, >= 0                          |
| booleana   | `bool`  | estricto: 1 o 0 no valen               |
| escala     | `int`   | de 1 a `escala_max`                    |
| conteo     | `int`   | >= 0                                   |
| categórica | `str`   | una de `categorias`; sin serie numérica |
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum

from modules.tracking.domain.errores import (
    CategoriaDesconocida,
    DefinicionInvalida,
    EntradaInvalida,
    TipoIncorrecto,
    ValorFueraDeRango,
)

type ValorMetrica = float | int | bool | str


class TipoMetrica(StrEnum):
    NUMERICA = "numerica"
    DURACION = "duracion"
    BOOLEANA = "booleana"
    ESCALA = "escala"
    CONTEO = "conteo"
    CATEGORICA = "categorica"


class Agregacion(StrEnum):
    """Cómo se resumen varias lecturas del mismo día (solo importa con keep_all)."""

    SUMA = "suma"
    MEDIA = "media"
    ULTIMA = "ultima"


class PoliticaDuplicado(StrEnum):
    """Qué pasa al registrar otra vez la misma métrica el mismo día."""

    REPLACE = "replace"
    KEEP_ALL = "keep_all"


_CON_RANGO = {TipoMetrica.NUMERICA, TipoMetrica.DURACION, TipoMetrica.CONTEO}
_ENTEROS = {TipoMetrica.DURACION, TipoMetrica.ESCALA, TipoMetrica.CONTEO}


def _nuevo_id() -> str:
    return str(uuid.uuid4())


@dataclass(frozen=True, kw_only=True)
class MetricEntry:
    """Un valor ya validado de una métrica en un día lógico."""

    metric_id: str
    valor: ValorMetrica
    timestamp: datetime
    logical_date: date
    slot: int = 0
    id: str = field(default_factory=_nuevo_id)

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise EntradaInvalida("El timestamp debe llevar zona horaria")
        if self.slot < 0:
            raise EntradaInvalida(f"El slot no puede ser negativo: {self.slot}")


@dataclass(frozen=True, kw_only=True)
class MetricDefinition:
    """Configuración de una métrica; valida sus propios valores."""

    nombre: str
    unidad: str
    tipo: TipoMetrica
    agregacion: Agregacion = Agregacion.ULTIMA
    on_duplicate: PoliticaDuplicado = PoliticaDuplicado.REPLACE
    objetivo: float | None = None
    minimo: float | None = None
    maximo: float | None = None
    escala_max: int | None = None
    categorias: tuple[str, ...] = ()
    activa: bool = True  # una métrica inactiva conserva sus datos pero no se pide a diario
    id: str = field(default_factory=_nuevo_id)

    def __post_init__(self) -> None:
        if not self.nombre.strip():
            raise DefinicionInvalida("El nombre de la métrica no puede estar vacío")
        self._comprobar_rango()
        self._comprobar_escala()
        self._comprobar_categorias()

    # --- Coherencia de la definición ---------------------------------------------------

    def _comprobar_rango(self) -> None:
        tiene_rango = self.minimo is not None or self.maximo is not None
        if tiene_rango and self.tipo not in _CON_RANGO:
            raise DefinicionInvalida(f"Una métrica {self.tipo} no admite mínimo ni máximo")
        if self.minimo is not None and self.maximo is not None and self.minimo > self.maximo:
            raise DefinicionInvalida(f"Mínimo {self.minimo} mayor que máximo {self.maximo}")

    def _comprobar_escala(self) -> None:
        if self.tipo is TipoMetrica.ESCALA:
            if self.escala_max is None or self.escala_max < 2:
                raise DefinicionInvalida("Una escala necesita escala_max >= 2")
        elif self.escala_max is not None:
            raise DefinicionInvalida(f"Una métrica {self.tipo} no admite escala_max")

    def _comprobar_categorias(self) -> None:
        if self.tipo is not TipoMetrica.CATEGORICA:
            if self.categorias:
                raise DefinicionInvalida(f"Una métrica {self.tipo} no admite categorías")
            return
        if not self.categorias:
            raise DefinicionInvalida("Una métrica categórica necesita categorías")
        if any(not c.strip() for c in self.categorias):
            raise DefinicionInvalida("Las categorías no pueden estar vacías")
        if len(set(self.categorias)) != len(self.categorias):
            raise DefinicionInvalida("Hay categorías repetidas")
        if self.objetivo is not None:
            raise DefinicionInvalida("Una métrica categórica no admite objetivo")
        if self.agregacion is not Agregacion.ULTIMA:
            raise DefinicionInvalida("Una métrica categórica solo admite agregación 'ultima'")

    # --- Validación de valores ---------------------------------------------------------

    def validar(self, valor: object) -> ValorMetrica:
        """Comprueba `valor` según el tipo de la métrica y lo devuelve normalizado."""
        match self.tipo:
            case TipoMetrica.BOOLEANA:
                if not isinstance(valor, bool):
                    raise TipoIncorrecto(self.nombre, valor, "se esperaba true o false")
                return valor
            case TipoMetrica.CATEGORICA:
                return self._validar_categoria(valor)
            case TipoMetrica.NUMERICA:
                return self._validar_numero(valor)
            case _:
                return self._validar_entero(valor)

    def _validar_categoria(self, valor: object) -> str:
        if not isinstance(valor, str):
            raise TipoIncorrecto(self.nombre, valor, "se esperaba una categoría (texto)")
        if valor not in self.categorias:
            raise CategoriaDesconocida(self.nombre, valor, f"válidas: {list(self.categorias)}")
        return valor

    def _validar_numero(self, valor: object) -> float:
        if isinstance(valor, bool) or not isinstance(valor, int | float):
            raise TipoIncorrecto(self.nombre, valor, "se esperaba un número")
        numero = float(valor)
        if not math.isfinite(numero):
            raise ValorFueraDeRango(self.nombre, valor, "debe ser un número finito")
        self._comprobar_limites(numero, self.minimo, self.maximo)
        return numero

    def _validar_entero(self, valor: object) -> int:
        if isinstance(valor, bool) or not isinstance(valor, int):
            raise TipoIncorrecto(self.nombre, valor, "se esperaba un número entero")
        if self.tipo is TipoMetrica.ESCALA:
            self._comprobar_limites(valor, 1, self.escala_max)
        else:  # duración (minutos) y conteo: nunca negativos
            minimo = 0 if self.minimo is None else max(0, self.minimo)
            self._comprobar_limites(valor, minimo, self.maximo)
        return valor

    def _comprobar_limites(self, valor: float, minimo: float | None, maximo: float | None) -> None:
        if minimo is not None and valor < minimo:
            raise ValorFueraDeRango(self.nombre, valor, f"mínimo {minimo}")
        if maximo is not None and valor > maximo:
            raise ValorFueraDeRango(self.nombre, valor, f"máximo {maximo}")

    # --- Fábrica de entradas -----------------------------------------------------------

    def crear_entrada(
        self, valor: object, *, timestamp: datetime, logical_date: date, slot: int = 0
    ) -> MetricEntry:
        """Valida `valor` y crea la entrada de esta métrica para `logical_date`."""
        return MetricEntry(
            metric_id=self.id,
            valor=self.validar(valor),
            timestamp=timestamp,
            logical_date=logical_date,
            slot=slot,
        )
