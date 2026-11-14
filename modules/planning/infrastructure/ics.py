"""Lector de calendarios .ics (iCalendar): convierte un fichero en eventos de planning.

- Los eventos recurrentes (RRULE) se expanden dentro de una ventana [desde, hasta], quitando
  las fechas de EXDATE y aplicando las ocurrencias modificadas (RECURRENCE-ID).
- Cada ocurrencia lleva un `uid_externo` estable: el UID del .ics y, si se repite, el instante
  de esa ocurrencia en UTC. Así reimportar el mismo calendario no duplica nada.
- Las horas sin zona («flotantes») se entienden en la zona del usuario.
- Se omiten, avisando, los eventos de día completo y los cancelados.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from dateutil.rrule import rruleset, rrulestr
from icalendar import Calendar
from icalendar import Event as VEvent
from icalendar.error import IncompleteComponent

from modules.planning.domain.errores import CalendarioInvalido, EventoInvalido
from modules.planning.domain.eventos import Evento, LecturaCalendario, OrigenEvento


class LectorIcs:
    """Implementa el port `LectorCalendario` con la librería `icalendar`."""

    def __init__(self, zona: str) -> None:
        self._zona = ZoneInfo(zona)

    def leer(self, contenido: bytes, desde: date, hasta: date) -> LecturaCalendario:
        """Eventos del .ics que empiezan entre `desde` y `hasta` (incluidos), en hora local."""
        try:
            calendario = Calendar.from_ical(contenido)
        except ValueError as error:
            raise CalendarioInvalido(f"No es un fichero .ics válido: {error}") from error
        if calendario.name != "VCALENDAR":
            raise CalendarioInvalido("El fichero no contiene un VCALENDAR")

        inicio = datetime.combine(desde, time(0), tzinfo=self._zona)
        fin = datetime.combine(hasta + timedelta(days=1), time(0), tzinfo=self._zona)
        lectura = LecturaCalendario()
        por_clave: dict[str, Evento] = {}
        vevents = list(calendario.walk("VEVENT"))
        # Primero los eventos «normales» y luego las ocurrencias modificadas, que los sustituyen.
        vevents.sort(key=lambda v: v.get("RECURRENCE-ID") is not None)
        for vevent in vevents:
            self._leer_vevent(vevent, inicio, fin, por_clave, lectura)
        lectura.eventos = sorted(por_clave.values(), key=lambda e: (e.inicio, e.titulo))
        return lectura

    def _leer_vevent(
        self,
        vevent: VEvent,
        ventana_inicio: datetime,
        ventana_fin: datetime,
        por_clave: dict[str, Evento],
        lectura: LecturaCalendario,
    ) -> None:
        titulo = str(vevent.get("SUMMARY", "")).strip() or "(sin título)"
        uid = str(vevent.get("UID", "")).strip()
        if not uid:
            lectura.omitidos.append(f"«{titulo}»: no tiene UID")
            return
        try:
            inicio, fin = vevent.start, vevent.end
        except IncompleteComponent:
            lectura.omitidos.append(f"«{titulo}»: no tiene inicio o fin")
            return
        if not isinstance(inicio, datetime):
            lectura.omitidos.append(f"«{titulo}»: es de día completo")
            return
        inicio, fin = self._con_zona(inicio), self._con_zona(fin)
        duracion = fin - inicio
        lugar = str(vevent.get("LOCATION", "")).strip() or None

        recurrence_id = vevent.get("RECURRENCE-ID")
        if recurrence_id is not None:
            original = self._con_zona(recurrence_id.dt)
            clave = _clave(uid, original)
            if str(vevent.get("STATUS", "")).upper() == "CANCELLED":
                por_clave.pop(clave, None)  # una ocurrencia anulada desaparece
                return
            if clave in por_clave or ventana_inicio <= inicio < ventana_fin:
                self._añadir(por_clave, lectura, clave, titulo, inicio, fin, lugar)
            return

        if str(vevent.get("STATUS", "")).upper() == "CANCELLED":
            lectura.omitidos.append(f"«{titulo}»: está cancelado")
            return

        if not vevent.get("RRULE"):
            if ventana_inicio <= inicio < ventana_fin:
                self._añadir(por_clave, lectura, uid, titulo, inicio, fin, lugar)
            return

        try:
            ocurrencias = self._expandir(vevent, inicio, ventana_inicio, ventana_fin)
        except ValueError as error:
            lectura.omitidos.append(f"«{titulo}»: regla de repetición no válida ({error})")
            return
        for ocurrencia in ocurrencias:
            self._añadir(
                por_clave,
                lectura,
                _clave(uid, ocurrencia),
                titulo,
                ocurrencia,
                ocurrencia + duracion,
                lugar,
            )

    def _expandir(
        self, vevent: VEvent, inicio: datetime, desde: datetime, hasta: datetime
    ) -> list[datetime]:
        reglas = rruleset()
        for regla in vevent.rrules:
            reglas.rrule(rrulestr(regla.to_ical().decode(), dtstart=inicio))
        for excluida in vevent.exdates:
            if isinstance(excluida, datetime):
                reglas.exdate(self._con_zona(excluida))
        return [self._con_zona(o) for o in reglas.between(desde, hasta, inc=True) if o < hasta]

    def _con_zona(self, instante: datetime) -> datetime:
        return instante if instante.tzinfo is not None else instante.replace(tzinfo=self._zona)

    @staticmethod
    def _añadir(
        por_clave: dict[str, Evento],
        lectura: LecturaCalendario,
        clave: str,
        titulo: str,
        inicio: datetime,
        fin: datetime,
        lugar: str | None,
    ) -> None:
        try:
            por_clave[clave] = Evento(
                titulo=titulo,
                inicio=inicio,
                fin=fin,
                lugar=lugar,
                origen=OrigenEvento.ICS,
                uid_externo=clave,
            )
        except EventoInvalido as error:
            lectura.omitidos.append(f"«{titulo}»: {error}")


def _clave(uid: str, ocurrencia: datetime) -> str:
    """UID de una ocurrencia concreta: «uid@20261116T080000Z»."""
    return f"{uid}@{ocurrencia.astimezone(UTC):%Y%m%dT%H%M%SZ}"
