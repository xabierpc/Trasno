"""Reglas de negocio de agenda: tareas y eventos.

Recibe al jarvis para leer configuracion y, si hace falta, pedir otros modulos
con jarvis.obtener(nombre). Nunca importa otro modulo directamente.

Fechas: dias 'YYYY-MM-DD'; momentos de evento 'YYYY-MM-DD HH:MM'.
"""

from datetime import date, datetime, timedelta

from trasno.modulos.agenda import repositorio

ESTADOS = ("pendiente", "en_curso", "hecha", "cancelada")
PRIORIDADES = (1, 2, 3)


def _texto(valor):
    """Quita espacios; '' pasa a None."""
    if valor is None:
        return None
    valor = valor.strip()
    if valor == "":
        return None
    return valor


def _iso(dia):
    if dia is None:
        return None
    if isinstance(dia, date):
        return dia.isoformat()
    return dia


# ---------- tareas ----------
def _validar_tarea(titulo, fecha, fecha_limite, prioridad):
    if titulo is None:
        raise ValueError("La tarea necesita un título")
    if prioridad not in PRIORIDADES:
        raise ValueError("La prioridad va de 1 (alta) a 3 (baja)")
    if fecha is not None and fecha_limite is not None and fecha_limite < fecha:
        raise ValueError("La fecha límite no puede ser anterior al día planificado")


def crear_tarea(jarvis, titulo, descripcion=None, fecha=None, fecha_limite=None, prioridad=2):
    titulo = _texto(titulo)
    fecha = _iso(fecha)
    fecha_limite = _iso(fecha_limite)
    _validar_tarea(titulo, fecha, fecha_limite, prioridad)
    return repositorio.crear_tarea(jarvis.user_id, titulo, _texto(descripcion), fecha, fecha_limite, prioridad)


def editar_tarea(jarvis, tarea_id, titulo, descripcion, fecha, fecha_limite, prioridad, estado):
    titulo = _texto(titulo)
    fecha = _iso(fecha)
    fecha_limite = _iso(fecha_limite)
    _validar_tarea(titulo, fecha, fecha_limite, prioridad)
    if estado not in ESTADOS:
        raise ValueError("Estado desconocido: " + str(estado))
    valores = {
        "titulo": titulo,
        "descripcion": _texto(descripcion),
        "fecha": fecha,
        "fecha_limite": fecha_limite,
        "prioridad": prioridad,
    }
    repositorio.actualizar_tarea(jarvis.user_id, tarea_id, valores)
    cambiar_estado(jarvis, tarea_id, estado)


def cambiar_estado(jarvis, tarea_id, estado):
    """Al marcarla como hecha se apunta cuando; si deja de estar hecha se borra."""
    if estado not in ESTADOS:
        raise ValueError("Estado desconocido: " + str(estado))
    actual = repositorio.obtener_tarea(jarvis.user_id, tarea_id)
    if actual is None:
        raise ValueError("Esa tarea ya no existe")
    if actual["estado"] == estado:
        return
    completada_en = None
    if estado == "hecha":
        completada_en = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    repositorio.actualizar_tarea(jarvis.user_id, tarea_id, {"estado": estado, "completada_en": completada_en})


def borrar_tarea(jarvis, tarea_id):
    repositorio.borrar_tarea(jarvis.user_id, tarea_id)


def tareas(jarvis, estados=ESTADOS):
    return repositorio.listar_tareas(jarvis.user_id, estados)


# ---------- eventos ----------
def _momento(dia, hora):
    """date + time -> 'YYYY-MM-DD HH:MM'."""
    return _iso(dia) + " " + hora.strftime("%H:%M")


def _validar_evento(titulo, inicio, fin):
    if titulo is None:
        raise ValueError("El evento necesita un título")
    if fin <= inicio:
        raise ValueError("El evento tiene que acabar después de empezar")


def solapes_evento(jarvis, inicio, fin, ignorar_id=None):
    """Textos de lo que pisa el intervalo: otros eventos y, si el modulo horario esta, sus bloques.

    Solo avisa: la regla del proyecto es avisar pero dejar guardar.
    """
    avisos = []
    for evento in repositorio.eventos_entre(jarvis.user_id, inicio, fin):
        if evento["id"] != ignorar_id:
            avisos.append("evento «" + evento["titulo"] + "» (" + evento["inicio"][11:] + "–" + evento["fin"][11:] + ")")

    horario = jarvis.obtener("horario")
    if horario is not None:
        dia = date.fromisoformat(inicio[:10])
        ultimo = date.fromisoformat(fin[:10])
        while dia <= ultimo:
            for bloque in horario.bloques_del_dia(jarvis, dia.isoformat()):
                if bloque["cancelado"]:
                    continue
                desde = dia.isoformat() + " " + bloque["hora_inicio"]
                hasta = dia.isoformat() + " " + bloque["hora_fin"]
                if desde < fin and hasta > inicio:
                    avisos.append(bloque["tipo"] + " «" + bloque["titulo"] + "» (" + bloque["hora_inicio"] + "–" + bloque["hora_fin"] + ")")
            dia = dia + timedelta(days=1)
    return avisos


def crear_evento(jarvis, titulo, dia_inicio, hora_inicio, dia_fin, hora_fin, ubicacion=None, descripcion=None):
    """Guarda el evento y devuelve la lista de solapes (vacia si no hay)."""
    titulo = _texto(titulo)
    if dia_fin is None:
        dia_fin = dia_inicio
    inicio = _momento(dia_inicio, hora_inicio)
    fin = _momento(dia_fin, hora_fin)
    _validar_evento(titulo, inicio, fin)
    solapes = solapes_evento(jarvis, inicio, fin)
    repositorio.crear_evento(jarvis.user_id, titulo, _texto(descripcion), inicio, fin, _texto(ubicacion))
    return solapes


def editar_evento(jarvis, evento_id, titulo, dia_inicio, hora_inicio, dia_fin, hora_fin, ubicacion, descripcion):
    titulo = _texto(titulo)
    if dia_fin is None:
        dia_fin = dia_inicio
    inicio = _momento(dia_inicio, hora_inicio)
    fin = _momento(dia_fin, hora_fin)
    _validar_evento(titulo, inicio, fin)
    solapes = solapes_evento(jarvis, inicio, fin, ignorar_id=evento_id)
    valores = {
        "titulo": titulo,
        "descripcion": _texto(descripcion),
        "inicio": inicio,
        "fin": fin,
        "ubicacion": _texto(ubicacion),
    }
    repositorio.actualizar_evento(jarvis.user_id, evento_id, valores)
    return solapes


def borrar_evento(jarvis, evento_id):
    repositorio.borrar_evento(jarvis.user_id, evento_id)


def eventos_del_dia(jarvis, fecha):
    siguiente = (date.fromisoformat(fecha) + timedelta(days=1)).isoformat()
    return repositorio.eventos_entre(jarvis.user_id, fecha + " 00:00", siguiente + " 00:00")


def eventos_de_semana(jarvis, lunes):
    """dict 'YYYY-MM-DD' -> eventos de ese dia, de lunes a domingo."""
    semana = {}
    for i in range(7):
        dia = (lunes + timedelta(days=i)).isoformat()
        semana[dia] = eventos_del_dia(jarvis, dia)
    return semana


# ---------- semana ----------
def tareas_de_semana(jarvis, lunes):
    """dict 'YYYY-MM-DD' -> tareas planificadas para ese dia, de lunes a domingo."""
    semana = {}
    for i in range(7):
        dia = (lunes + timedelta(days=i)).isoformat()
        semana[dia] = [t for t in repositorio.tareas_del_dia(jarvis.user_id, dia) if t["fecha"] == dia]
    return semana


def horario_de_semana(jarvis, lunes):
    """dict dia -> bloques del modulo horario, o None si ese modulo no esta activo."""
    horario = jarvis.obtener("horario")
    if horario is None:
        return None
    semana = {}
    for i in range(7):
        dia = (lunes + timedelta(days=i)).isoformat()
        semana[dia] = horario.bloques_del_dia(jarvis, dia)
    return semana


def tareas_para_inicio(jarvis, fecha):
    """Lo que hay que hacer: las de ese dia (planificadas o que vencen) y las arrastradas.

    Las hechas o canceladas de hoy se quedan (tachadas) para ver el progreso del dia.
    """
    return {
        "hoy": repositorio.tareas_del_dia(jarvis.user_id, fecha),
        "arrastradas": repositorio.tareas_atrasadas(jarvis.user_id, fecha),
    }


# ---------- dias importantes ----------
def marcar_importante(jarvis, fecha, nota=None):
    repositorio.marcar_dia(jarvis.user_id, _iso(fecha), _texto(nota))


def desmarcar_importante(jarvis, fecha):
    repositorio.desmarcar_dia(jarvis.user_id, _iso(fecha))


def dias_importantes(jarvis, desde, hasta):
    """dict 'YYYY-MM-DD' -> nota ('' si no tiene)."""
    resultado = {}
    for fila in repositorio.dias_importantes_entre(jarvis.user_id, _iso(desde), _iso(hasta)):
        resultado[fila["fecha"]] = fila["nota"] or ""
    return resultado


def resumen(jarvis, fecha):
    """Texto corto para la portada, o None."""
    tareas_dia = repositorio.tareas_del_dia(jarvis.user_id, fecha)
    hechas = len([t for t in tareas_dia if t["estado"] == "hecha"])
    eventos = eventos_del_dia(jarvis, fecha)
    importante = dias_importantes(jarvis, fecha, fecha)
    if len(tareas_dia) == 0 and len(eventos) == 0 and len(importante) == 0:
        return None
    partes = []
    if fecha in importante:
        partes.append("día importante" + _con_nota(importante[fecha]))
    if len(tareas_dia) > 0:
        partes.append(str(hechas) + "/" + str(len(tareas_dia)) + " tareas hechas")
    if len(eventos) > 0:
        if len(eventos) == 1:
            partes.append("1 evento")
        else:
            partes.append(str(len(eventos)) + " eventos")
    return ", ".join(partes)


def _con_nota(nota):
    if nota:
        return " (" + nota + ")"
    return ""
