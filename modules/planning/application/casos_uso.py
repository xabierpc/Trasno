"""Casos de uso de planning. Cada método público es candidato a herramienta del agente."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from modules.planning.application.ports import (
    LectorCalendario,
    RepositorioBloques,
    RepositorioEventos,
    RepositorioTareas,
)
from modules.planning.domain.agenda import Agenda, agenda_del_dia, limites_del_dia
from modules.planning.domain.errores import (
    BloqueNoEncontrado,
    EventoNoEncontrado,
    TareaNoEncontrada,
)
from modules.planning.domain.eventos import (
    BloqueRecurrente,
    Evento,
    Ocurrencia,
    Solape,
    bloques_se_solapan,
    solapes,
)
from modules.planning.domain.tareas import Prioridad, Tarea

DIAS_ATRAS = 30
DIAS_ADELANTE = 365


def _ahora() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class EventoGuardado:
    """Resultado de guardar un evento: el evento y los avisos de solape (no impiden guardar)."""

    evento: Evento
    avisos: list[Solape]


@dataclass(frozen=True)
class ResultadoImportacion:
    """Qué ha pasado al importar un calendario: cuántos eventos nuevos, cambiados e iguales."""

    nuevos: int
    actualizados: int
    sin_cambios: int
    omitidos: list[str]


@dataclass(frozen=True)
class BloqueGuardado:
    """Resultado de guardar un bloque: el bloque y los bloques con los que se pisa."""

    bloque: BloqueRecurrente
    avisos: list[BloqueRecurrente]


class CasosUsoPlanning:
    """Operaciones de planning sobre los repositorios de un usuario.

    `zona` es la zona horaria del usuario: decide qué es «un día» para la agenda y en qué hora
    se expanden los bloques recurrentes.
    """

    def __init__(
        self,
        tareas: RepositorioTareas,
        eventos: RepositorioEventos,
        bloques: RepositorioBloques,
        zona: str,
        reloj: Callable[[], datetime] = _ahora,
        lector: LectorCalendario | None = None,
    ) -> None:
        self._tareas = tareas
        self._eventos = eventos
        self._bloques = bloques
        self._zona = zona
        self._reloj = reloj
        self._lector = lector

    # --- Tareas -------------------------------------------------------------------------------

    def crear_tarea(
        self,
        titulo: str,
        fecha: date | None = None,
        prioridad: Prioridad = Prioridad.MEDIA,
        estimacion_min: int | None = None,
    ) -> Tarea:
        """Crea una tarea pendiente, para el día `fecha` o sin día si no se indica."""
        tarea = Tarea(
            titulo=titulo,
            fecha=fecha,
            prioridad=Prioridad(prioridad),
            estimacion_min=estimacion_min,
            creada_en=self._reloj(),
        )
        self._tareas.guardar(tarea)
        return tarea

    def completar_tarea(self, tarea_id: str) -> Tarea:
        """Marca una tarea como hecha."""
        return self._cambiar_tarea(tarea_id, lambda t: t.completar(self._reloj()))

    def reabrir_tarea(self, tarea_id: str) -> Tarea:
        """Vuelve a dejar pendiente una tarea hecha."""
        return self._cambiar_tarea(tarea_id, Tarea.reabrir)

    def mover_tarea(self, tarea_id: str, fecha: date | None) -> Tarea:
        """Pasa una tarea a otro día, o a ninguno si `fecha` es None."""
        return self._cambiar_tarea(tarea_id, lambda t: t.mover(fecha))

    def borrar_tarea(self, tarea_id: str) -> None:
        """Borra una tarea (borrado real)."""
        if not self._tareas.borrar(tarea_id):
            raise TareaNoEncontrada(tarea_id)

    def tareas_sin_fecha(self) -> list[Tarea]:
        """Tareas sin día asignado (bandeja de entrada)."""
        return self._tareas.sin_fecha()

    def _cambiar_tarea(self, tarea_id: str, cambio: Callable[[Tarea], Tarea]) -> Tarea:
        tarea = self._tareas.obtener(tarea_id)
        if tarea is None:
            raise TareaNoEncontrada(tarea_id)
        nueva = cambio(tarea)
        self._tareas.guardar(nueva)
        return nueva

    # --- Eventos ------------------------------------------------------------------------------

    def crear_evento(
        self, titulo: str, inicio: datetime, fin: datetime, lugar: str | None = None
    ) -> EventoGuardado:
        """Guarda un evento puntual y avisa de los eventos o clases con los que se pisa."""
        evento = Evento(titulo=titulo, inicio=inicio, fin=fin, lugar=lugar)
        avisos = self._solapes_de(evento)
        self._eventos.guardar(evento)
        return EventoGuardado(evento=evento, avisos=avisos)

    def mover_evento(self, evento_id: str, inicio: datetime, fin: datetime) -> EventoGuardado:
        """Cambia la hora de un evento y avisa de los nuevos solapes."""
        actual = self._eventos.obtener(evento_id)
        if actual is None:
            raise EventoNoEncontrado(evento_id)
        evento = replace(actual, inicio=inicio, fin=fin)
        avisos = self._solapes_de(evento)
        self._eventos.guardar(evento)
        return EventoGuardado(evento=evento, avisos=avisos)

    def borrar_evento(self, evento_id: str) -> None:
        """Borra un evento (borrado real)."""
        if not self._eventos.borrar(evento_id):
            raise EventoNoEncontrado(evento_id)

    def _solapes_de(self, evento: Evento) -> list[Solape]:
        existentes: list[Evento | Ocurrencia] = [*self._eventos.entre(evento.inicio, evento.fin)]
        # Un evento puede cruzar la medianoche: se miran los bloques de cada día que toca.
        primer_dia = evento.inicio.astimezone(ZoneInfo(self._zona)).date()
        ultimo_dia = evento.fin.astimezone(ZoneInfo(self._zona)).date()
        for bloque in self._bloques.listar():
            existentes += bloque.ocurrencias(primer_dia, ultimo_dia, self._zona)
        return solapes(evento, existentes)

    def importar_calendario(self, contenido: bytes) -> ResultadoImportacion:
        """Importa un .ics: crea los eventos nuevos y actualiza los ya importados (por su UID).

        Solo se leen los eventos desde hace `DIAS_ATRAS` hasta dentro de `DIAS_ADELANTE`.
        Los eventos que ya no estén en el fichero no se borran.
        """
        if self._lector is None:
            raise RuntimeError("CasosUsoPlanning se creó sin lector de calendarios")
        hoy = self._reloj().astimezone(ZoneInfo(self._zona)).date()
        lectura = self._lector.leer(
            contenido, hoy - timedelta(days=DIAS_ATRAS), hoy + timedelta(days=DIAS_ADELANTE)
        )
        nuevos = actualizados = sin_cambios = 0
        for leido in lectura.eventos:
            assert leido.uid_externo is not None  # el lector siempre lo rellena
            existente = self._eventos.por_uid(leido.uid_externo)
            if existente is None:
                self._eventos.guardar(leido)
                nuevos += 1
                continue
            actualizado = replace(leido, id=existente.id)
            if actualizado == existente:
                sin_cambios += 1
            else:
                self._eventos.guardar(actualizado)
                actualizados += 1
        return ResultadoImportacion(nuevos, actualizados, sin_cambios, lectura.omitidos)

    # --- Bloques recurrentes ------------------------------------------------------------------

    def crear_bloque(
        self,
        titulo: str,
        dia_semana: int,
        hora_inicio: time,
        hora_fin: time,
        desde: date | None = None,
        hasta: date | None = None,
        lugar: str | None = None,
    ) -> BloqueGuardado:
        """Guarda un bloque semanal (0 = lunes) y avisa de los bloques con los que se pisa."""
        bloque = BloqueRecurrente(
            titulo=titulo,
            dia_semana=dia_semana,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            desde=desde,
            hasta=hasta,
            lugar=lugar,
        )
        avisos = [b for b in self._bloques.listar() if bloques_se_solapan(bloque, b)]
        self._bloques.guardar(bloque)
        return BloqueGuardado(bloque=bloque, avisos=avisos)

    def listar_bloques(self) -> list[BloqueRecurrente]:
        """Todos los bloques recurrentes, por día de la semana y hora."""
        return self._bloques.listar()

    def borrar_bloque(self, bloque_id: str) -> None:
        """Borra un bloque recurrente (deja de aparecer en todas las semanas)."""
        if not self._bloques.borrar(bloque_id):
            raise BloqueNoEncontrado(bloque_id)

    # --- Agenda -------------------------------------------------------------------------------

    def agenda(self, dia: date) -> Agenda:
        """Citas, tareas del día y tareas atrasadas de `dia`."""
        inicio, fin = limites_del_dia(dia, self._zona)
        return agenda_del_dia(
            dia,
            self._zona,
            eventos=self._eventos.entre(inicio, fin),
            bloques=self._bloques.listar(),
            tareas=self._tareas.del_dia(dia),
            atrasadas=self._tareas.atrasadas(dia),
        )
