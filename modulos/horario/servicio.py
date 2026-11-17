"""Reglas de negocio de horario: horario semanal de clase y trabajo.

Recibe al jarvis para leer configuracion y, si hace falta, pedir otros modulos
con jarvis.obtener(nombre). Nunca importa otro modulo directamente.

Horas 'HH:MM'; dias 'YYYY-MM-DD'; dia_semana 0 = lunes.
"""

from datetime import date, time, timedelta

from modulos.horario import repositorio
from nucleo.fechas import DIAS_SEMANA

TIPOS = ("clase", "trabajo", "otro")


def _texto(valor):
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


def _hhmm(hora):
    if isinstance(hora, time):
        return hora.strftime("%H:%M")
    return hora


# ---------- bloques ----------
def _validar_bloque(tipo, titulo, hora_inicio, hora_fin, desde, hasta):
    if tipo not in TIPOS:
        raise ValueError("Tipo desconocido: " + str(tipo))
    if titulo is None:
        raise ValueError("El bloque necesita un título")
    if hora_fin <= hora_inicio:
        raise ValueError("La hora de fin tiene que ser posterior a la de inicio")
    if desde is None:
        raise ValueError("Falta desde cuándo está vigente")
    if hasta is not None and hasta < desde:
        raise ValueError("«Vigente hasta» no puede ser anterior a «vigente desde»")


def _se_pisan_fechas(desde_a, hasta_a, desde_b, hasta_b):
    fin_a = hasta_a or "9999-12-31"
    fin_b = hasta_b or "9999-12-31"
    return desde_a <= fin_b and desde_b <= fin_a


def solapes_bloque(jarvis, dia_semana, hora_inicio, hora_fin, desde, hasta, ignorar_id=None):
    """Otros bloques del mismo dia que pisan las horas en algun periodo de vigencia. Solo avisa."""
    avisos = []
    for otro in repositorio.bloques_mismo_dia(jarvis.user_id, dia_semana):
        if otro["id"] == ignorar_id:
            continue
        if not _se_pisan_fechas(desde, hasta, otro["vigente_desde"], otro["vigente_hasta"]):
            continue
        if hora_inicio < otro["hora_fin"] and otro["hora_inicio"] < hora_fin:
            avisos.append(
                DIAS_SEMANA[dia_semana] + " «" + otro["titulo"] + "» (" + otro["hora_inicio"] + "–" + otro["hora_fin"] + ")"
            )
    return avisos


def crear_bloques(jarvis, tipo, titulo, dias_semana, hora_inicio, hora_fin, ubicacion, desde, hasta=None):
    """Crea un bloque por cada dia elegido (p. ej. la misma clase lunes y miercoles).

    Devuelve la lista de solapes (vacia si no hay); se guarda igualmente.
    """
    titulo = _texto(titulo)
    hora_inicio = _hhmm(hora_inicio)
    hora_fin = _hhmm(hora_fin)
    desde = _iso(desde)
    hasta = _iso(hasta)
    _validar_bloque(tipo, titulo, hora_inicio, hora_fin, desde, hasta)
    if len(dias_semana) == 0:
        raise ValueError("Elige al menos un día de la semana")

    solapes = []
    for dia_semana in dias_semana:
        solapes = solapes + solapes_bloque(jarvis, dia_semana, hora_inicio, hora_fin, desde, hasta)
    for dia_semana in dias_semana:
        repositorio.crear_bloque(
            jarvis.user_id, tipo, titulo, dia_semana, hora_inicio, hora_fin, _texto(ubicacion), desde, hasta
        )
    return solapes


def editar_bloque(jarvis, bloque_id, tipo, titulo, dia_semana, hora_inicio, hora_fin, ubicacion, desde, hasta):
    titulo = _texto(titulo)
    hora_inicio = _hhmm(hora_inicio)
    hora_fin = _hhmm(hora_fin)
    desde = _iso(desde)
    hasta = _iso(hasta)
    _validar_bloque(tipo, titulo, hora_inicio, hora_fin, desde, hasta)
    solapes = solapes_bloque(jarvis, dia_semana, hora_inicio, hora_fin, desde, hasta, ignorar_id=bloque_id)
    valores = {
        "tipo": tipo,
        "titulo": titulo,
        "dia_semana": dia_semana,
        "hora_inicio": hora_inicio,
        "hora_fin": hora_fin,
        "ubicacion": _texto(ubicacion),
        "vigente_desde": desde,
        "vigente_hasta": hasta,
    }
    repositorio.actualizar_bloque(jarvis.user_id, bloque_id, valores)
    return solapes


def borrar_bloque(jarvis, bloque_id):
    """Borrado real; sus excepciones caen con el (ON DELETE CASCADE)."""
    repositorio.borrar_bloque(jarvis.user_id, bloque_id)


def bloques(jarvis):
    return repositorio.listar_bloques(jarvis.user_id)


# ---------- excepciones ----------
def guardar_excepcion(jarvis, bloque_id, fecha, cancelado, hora_inicio=None, hora_fin=None, motivo=None):
    """Cancela o cambia de hora un bloque un dia concreto."""
    fecha = _iso(fecha)
    bloque = repositorio.obtener_bloque(jarvis.user_id, bloque_id)
    if bloque is None:
        raise ValueError("Ese bloque ya no existe")
    if date.fromisoformat(fecha).weekday() != bloque["dia_semana"]:
        raise ValueError("«" + bloque["titulo"] + "» es los " + DIAS_SEMANA[bloque["dia_semana"]].lower() + ": elige un día que caiga en " + DIAS_SEMANA[bloque["dia_semana"]].lower())
    if fecha < bloque["vigente_desde"] or (bloque["vigente_hasta"] is not None and fecha > bloque["vigente_hasta"]):
        raise ValueError("Ese día el bloque no está vigente")

    if cancelado:
        tipo = "cancelado"
        hora_inicio = None
        hora_fin = None
    else:
        tipo = "modificado"
        hora_inicio = _hhmm(hora_inicio)
        hora_fin = _hhmm(hora_fin)
        if hora_inicio is None or hora_fin is None or hora_fin <= hora_inicio:
            raise ValueError("Pon una hora de inicio y una de fin posterior")
    repositorio.guardar_excepcion(jarvis.user_id, bloque_id, fecha, tipo, hora_inicio, hora_fin, _texto(motivo))


def borrar_excepcion(jarvis, excepcion_id):
    repositorio.borrar_excepcion(jarvis.user_id, excepcion_id)


def proximas_excepciones(jarvis, desde):
    return repositorio.excepciones_desde(jarvis.user_id, _iso(desde))


# ---------- vistas ----------
def bloques_del_dia(jarvis, fecha):
    """Horario real de un dia, con las excepciones aplicadas.

    Devuelve dicts (no filas de SQLite) porque esto lo usan otros modulos
    a traves de Horario.bloques_del_dia. Claves:
    id, tipo, titulo, ubicacion, hora_inicio, hora_fin, cancelado, modificado, motivo.
    """
    fecha = _iso(fecha)
    dia_semana = date.fromisoformat(fecha).weekday()
    excepciones = repositorio.excepciones_del_dia(jarvis.user_id, fecha)
    resultado = []
    for bloque in repositorio.bloques_vigentes(jarvis.user_id, dia_semana, fecha):
        excepcion = excepciones.get(bloque["id"])
        item = {
            "id": bloque["id"],
            "tipo": bloque["tipo"],
            "titulo": bloque["titulo"],
            "ubicacion": bloque["ubicacion"],
            "hora_inicio": bloque["hora_inicio"],
            "hora_fin": bloque["hora_fin"],
            "cancelado": False,
            "modificado": False,
            "motivo": None,
        }
        if excepcion is not None:
            item["motivo"] = excepcion["motivo"]
            if excepcion["tipo"] == "cancelado":
                item["cancelado"] = True
            else:
                item["modificado"] = True
                item["hora_inicio"] = excepcion["hora_inicio"]
                item["hora_fin"] = excepcion["hora_fin"]
        resultado.append(item)
    resultado.sort(key=lambda b: b["hora_inicio"])
    return resultado


def semana(jarvis, lunes):
    """dict 'YYYY-MM-DD' -> bloques_del_dia, de lunes a domingo."""
    resultado = {}
    for i in range(7):
        dia = (lunes + timedelta(days=i)).isoformat()
        resultado[dia] = bloques_del_dia(jarvis, dia)
    return resultado


def horas_del_dia(jarvis, fecha):
    """Horas de clase/trabajo de un dia (sin contar lo cancelado)."""
    total = 0
    for bloque in bloques_del_dia(jarvis, fecha):
        if bloque["cancelado"]:
            continue
        h1, m1 = bloque["hora_inicio"].split(":")
        h2, m2 = bloque["hora_fin"].split(":")
        total = total + (int(h2) * 60 + int(m2)) - (int(h1) * 60 + int(m1))
    return total / 60


def resumen(jarvis, fecha):
    lista = [b for b in bloques_del_dia(jarvis, fecha) if not b["cancelado"]]
    if len(lista) == 0:
        return None
    horas = horas_del_dia(jarvis, fecha)
    nombre = " bloques ("
    if len(lista) == 1:
        nombre = " bloque ("
    return str(len(lista)) + nombre + ("%g" % round(horas, 2)) + " h), primero a las " + lista[0]["hora_inicio"]
