"""Reglas de negocio de entreno: rutina semanal y registro de fuerza y cardio.

Recibe al jarvis para leer configuracion y, si hace falta, pedir otros modulos
con jarvis.obtener(nombre). Nunca importa otro modulo directamente.

PR: no se guardan; se calculan juntando las series registradas con los PR
apuntados a mano. "PR a N reps" = mayor peso movido en una serie de N o mas reps.
"""

from datetime import date

from modulos.entreno import repositorio
from modulos.entreno.repositorio import EnUso

BASICOS = ("Sentadilla", "Press banca", "Peso muerto")
GRUPO_BASICO = {"Sentadilla": "Pierna", "Press banca": "Pecho", "Peso muerto": "Espalda"}
REPS_PR = (1, 3, 5, 8, 10)
TIPOS = ("fuerza", "cardio")


def _texto(valor):
    if valor is None:
        return None
    valor = valor.strip()
    if valor == "":
        return None
    return valor


def _iso(dia):
    if isinstance(dia, date):
        return dia.isoformat()
    return dia


def kg(valor):
    """100.0 -> '100', 102.5 -> '102.5'."""
    return "%g" % valor


# ======================================================================
# Ejercicios
# ======================================================================
def asegurar_basicos(jarvis):
    for nombre in BASICOS:
        repositorio.asegurar_ejercicio(jarvis.user_id, nombre, "fuerza", GRUPO_BASICO[nombre])


def ejercicios(jarvis, tipo=None):
    asegurar_basicos(jarvis)
    lista = repositorio.listar_ejercicios(jarvis.user_id)
    if tipo is None:
        return lista
    return [e for e in lista if e["tipo"] == tipo]


def basicos(jarvis):
    """Los tres basicos en orden fijo (filas de ejercicio)."""
    asegurar_basicos(jarvis)
    return [repositorio.ejercicio_por_nombre(jarvis.user_id, nombre) for nombre in BASICOS]


def crear_ejercicio(jarvis, nombre, tipo, grupo_muscular=None):
    nombre = _texto(nombre)
    if nombre is None:
        raise ValueError("El ejercicio necesita un nombre")
    if tipo not in TIPOS:
        raise ValueError("Tipo desconocido: " + str(tipo))
    if repositorio.ejercicio_por_nombre(jarvis.user_id, nombre) is not None:
        raise ValueError("Ya existe un ejercicio llamado «" + nombre + "»")
    return repositorio.crear_ejercicio(jarvis.user_id, nombre, tipo, _texto(grupo_muscular))


def borrar_ejercicio(jarvis, ejercicio_id):
    ejercicio = repositorio.obtener_ejercicio(jarvis.user_id, ejercicio_id)
    if ejercicio is None:
        return
    if ejercicio["nombre"] in BASICOS:
        raise ValueError("Los tres básicos no se pueden borrar")
    try:
        repositorio.borrar_ejercicio(jarvis.user_id, ejercicio_id)
    except EnUso:
        raise ValueError("«" + ejercicio["nombre"] + "» está en una rutina o en algún entreno; quítalo de ahí antes")


# ======================================================================
# Rutinas
# ======================================================================
def rutinas(jarvis):
    return repositorio.listar_rutinas(jarvis.user_id)


def rutina_activa(jarvis):
    return repositorio.rutina_activa(jarvis.user_id)


def crear_rutina(jarvis, nombre):
    """La primera rutina que se crea queda activa."""
    nombre = _texto(nombre)
    if nombre is None:
        raise ValueError("La rutina necesita un nombre")
    if any(r["nombre"] == nombre for r in rutinas(jarvis)):
        raise ValueError("Ya hay una rutina llamada «" + nombre + "»")
    rutina_id = repositorio.crear_rutina(jarvis.user_id, nombre)
    if rutina_activa(jarvis) is None:
        repositorio.activar_rutina(jarvis.user_id, rutina_id)
    return rutina_id


def activar_rutina(jarvis, rutina_id):
    repositorio.activar_rutina(jarvis.user_id, rutina_id)


def borrar_rutina(jarvis, rutina_id):
    """Borra el plan; los entrenos ya registrados se conservan (pierden el enlace al dia)."""
    repositorio.borrar_rutina(jarvis.user_id, rutina_id)


def dias_de_rutina(jarvis, rutina_id):
    """dict dia_semana (0 lunes) -> fila rutina_dia. Los que faltan son descanso."""
    resultado = {}
    for dia in repositorio.dias_de_rutina(jarvis.user_id, rutina_id):
        resultado[dia["dia_semana"]] = dia
    return resultado


def guardar_dia(jarvis, rutina_id, dia_semana, nombre):
    nombre = _texto(nombre)
    if nombre is None:
        raise ValueError("Ponle nombre al día (Pierna, Empuje, Full body…)")
    repositorio.guardar_dia_rutina(jarvis.user_id, rutina_id, dia_semana, nombre)


def quitar_dia(jarvis, rutina_dia_id):
    """El dia pasa a descanso; se borran sus ejercicios del plan."""
    repositorio.borrar_dia_rutina(jarvis.user_id, rutina_dia_id)


def ejercicios_de_dia(jarvis, rutina_dia_id):
    return repositorio.ejercicios_de_dia(jarvis.user_id, rutina_dia_id)


def anadir_a_dia(jarvis, rutina_dia_id, ejercicio_id, series=None, reps=None, peso_kg=None,
                 minutos=None, km=None):
    """Objetivos opcionales: fuerza usa series/reps/peso; cardio usa minutos/km."""
    ejercicio = repositorio.obtener_ejercicio(jarvis.user_id, ejercicio_id)
    if ejercicio is None:
        raise ValueError("Ese ejercicio ya no existe")
    for valor in (series, reps, peso_kg, minutos, km):
        if valor is not None and valor < 0:
            raise ValueError("Los objetivos no pueden ser negativos")
    duracion_s = None
    distancia_m = None
    if ejercicio["tipo"] == "fuerza":
        minutos = None
        km = None
    else:
        series = None
        reps = None
        peso_kg = None
        if minutos:
            duracion_s = int(round(minutos * 60))
        if km:
            distancia_m = km * 1000
    repositorio.anadir_a_dia(
        jarvis.user_id, rutina_dia_id, ejercicio_id, series or None, reps or None, peso_kg or None,
        duracion_s, distancia_m,
    )


def quitar_de_dia(jarvis, rutina_ejercicio_id):
    repositorio.quitar_de_dia(jarvis.user_id, rutina_ejercicio_id)


def objetivo_texto(fila):
    """'4 × 8 · 80 kg' o '30 min · 5 km' a partir de una fila de rutina_ejercicio."""
    trozos = []
    if fila["tipo"] == "fuerza":
        if fila["series_objetivo"] and fila["reps_objetivo"]:
            trozos.append(str(fila["series_objetivo"]) + " × " + str(fila["reps_objetivo"]))
        elif fila["series_objetivo"]:
            trozos.append(str(fila["series_objetivo"]) + " series")
        elif fila["reps_objetivo"]:
            trozos.append(str(fila["reps_objetivo"]) + " reps")
        if fila["peso_objetivo_kg"]:
            trozos.append(kg(fila["peso_objetivo_kg"]) + " kg")
    else:
        if fila["duracion_objetivo_s"]:
            trozos.append(kg(fila["duracion_objetivo_s"] / 60) + " min")
        if fila["distancia_objetivo_m"]:
            trozos.append(kg(fila["distancia_objetivo_m"] / 1000) + " km")
    return " · ".join(trozos)


# ======================================================================
# Registro
# ======================================================================
def plan_de(jarvis, fecha):
    """Lo que toca ese dia segun la rutina activa, o None si es descanso o no hay rutina.

    dict: rutina, dia (fila rutina_dia), ejercicios (filas con objetivos).
    """
    rutina = rutina_activa(jarvis)
    if rutina is None:
        return None
    dia = repositorio.dia_de_rutina(jarvis.user_id, rutina["id"], date.fromisoformat(_iso(fecha)).weekday())
    if dia is None:
        return None
    return {"rutina": rutina, "dia": dia, "ejercicios": ejercicios_de_dia(jarvis, dia["id"])}


def sesion_de(jarvis, fecha):
    return repositorio.sesion_de(jarvis.user_id, _iso(fecha))


def empezar_sesion(jarvis, fecha):
    """Abre la sesion del dia enlazada al dia de rutina que toque (si hay). Una por dia."""
    fecha = _iso(fecha)
    existente = sesion_de(jarvis, fecha)
    if existente is not None:
        return existente["id"]
    plan = plan_de(jarvis, fecha)
    rutina_dia_id = None
    if plan is not None:
        rutina_dia_id = plan["dia"]["id"]
    return repositorio.crear_sesion(jarvis.user_id, fecha, rutina_dia_id)


def guardar_notas(jarvis, sesion_id, notas):
    repositorio.actualizar_sesion(jarvis.user_id, sesion_id, {"notas": _texto(notas)})


def borrar_sesion(jarvis, sesion_id):
    """Borrado real de la sesion con todas sus series y cardio."""
    repositorio.borrar_sesion(jarvis.user_id, sesion_id)


def nombre_dia_sesion(jarvis, sesion):
    if sesion["rutina_dia_id"] is None:
        return None
    dia = repositorio.obtener_dia_rutina(jarvis.user_id, sesion["rutina_dia_id"])
    if dia is None:
        return None
    return dia["nombre"]


def series_por_ejercicio(jarvis, sesion_id):
    """dict ejercicio_id -> lista de series en orden."""
    resultado = {}
    for serie in repositorio.series_de_sesion(jarvis.user_id, sesion_id):
        resultado.setdefault(serie["ejercicio_id"], []).append(serie)
    return resultado


def cardio_por_ejercicio(jarvis, sesion_id):
    resultado = {}
    for fila in repositorio.cardio_de_sesion(jarvis.user_id, sesion_id):
        resultado.setdefault(fila["ejercicio_id"], []).append(fila)
    return resultado


def anadir_serie(jarvis, sesion_id, ejercicio_id, reps, peso_kg, rpe=None):
    """Guarda la serie y devuelve el texto de PR si la serie bate alguna marca de un basico, o None."""
    if reps is None or reps < 1:
        raise ValueError("Una serie necesita al menos 1 repetición")
    if peso_kg is None or peso_kg < 0:
        raise ValueError("El peso no puede ser negativo")
    if rpe is not None and (rpe < 1 or rpe > 10):
        raise ValueError("El RPE va de 1 a 10")

    ejercicio = repositorio.obtener_ejercicio(jarvis.user_id, ejercicio_id)
    batidas = []
    if ejercicio is not None and ejercicio["nombre"] in BASICOS and peso_kg > 0:
        for minimo in REPS_PR:
            if reps < minimo:
                continue
            anterior = repositorio.mejor_marca(jarvis.user_id, ejercicio_id, minimo)
            if anterior is not None and peso_kg > anterior["peso_kg"]:
                batidas.append(minimo)

    repositorio.anadir_serie(jarvis.user_id, sesion_id, ejercicio_id, reps, peso_kg, rpe)

    if len(batidas) == 0:
        return None
    texto = "Nuevo PR en " + ejercicio["nombre"] + ": " + kg(peso_kg) + " kg × " + str(reps)
    unidad = " reps)"
    if batidas == [1]:
        unidad = " rep)"
    return texto + " (mejora tu marca a " + _lista_reps(batidas) + unidad


def _lista_reps(numeros):
    textos = [str(n) for n in numeros]
    if len(textos) == 1:
        return textos[0]
    return ", ".join(textos[:-1]) + " y " + textos[-1]


def borrar_serie(jarvis, serie_id):
    repositorio.borrar_serie(jarvis.user_id, serie_id)


def anadir_cardio(jarvis, sesion_id, ejercicio_id, minutos, km=None, notas=None):
    if minutos is None or minutos <= 0:
        raise ValueError("Pon cuántos minutos")
    if km is not None and km < 0:
        raise ValueError("La distancia no puede ser negativa")
    distancia_m = None
    if km:
        distancia_m = km * 1000
    repositorio.anadir_cardio(
        jarvis.user_id, sesion_id, ejercicio_id, int(round(minutos * 60)), distancia_m, _texto(notas)
    )


def borrar_cardio(jarvis, cardio_id):
    repositorio.borrar_cardio(jarvis.user_id, cardio_id)


def historial(jarvis, limite=60):
    return repositorio.historial(jarvis.user_id, limite)


# ======================================================================
# PR
# ======================================================================
def tabla_prs(jarvis, ejercicio_id):
    """Lista de dicts {reps, marca} para cada N de REPS_PR; marca es None si no hay ninguna.

    marca: fila con peso_kg, reps (las que se hicieron de verdad), fecha y origen.
    """
    return [{"reps": n, "marca": repositorio.mejor_marca(jarvis.user_id, ejercicio_id, n)} for n in REPS_PR]


def anadir_pr_manual(jarvis, ejercicio_id, fecha, reps, peso_kg, notas=None):
    if reps is None or reps < 1:
        raise ValueError("Las repeticiones tienen que ser al menos 1")
    if peso_kg is None or peso_kg <= 0:
        raise ValueError("El peso tiene que ser mayor que 0")
    fecha = _iso(fecha)
    if fecha > date.today().isoformat():
        raise ValueError("Un PR no puede ser de una fecha futura")
    repositorio.crear_pr_manual(jarvis.user_id, ejercicio_id, fecha, reps, peso_kg, _texto(notas))


def borrar_pr_manual(jarvis, pr_id):
    repositorio.borrar_pr_manual(jarvis.user_id, pr_id)


def prs_manuales(jarvis):
    return repositorio.prs_manuales(jarvis.user_id)


def progreso(jarvis, ejercicio_id):
    """Filas (fecha, peso_kg) con el peso maximo de cada dia entrenado."""
    return repositorio.maximo_por_sesion(jarvis.user_id, ejercicio_id)


# ======================================================================
# Portada
# ======================================================================
def resumen(jarvis, fecha):
    sesion = sesion_de(jarvis, fecha)
    if sesion is None:
        plan = plan_de(jarvis, fecha)
        if plan is None:
            return None
        return "toca " + plan["dia"]["nombre"]
    partes = []
    nombre = nombre_dia_sesion(jarvis, sesion)
    if nombre:
        partes.append(nombre)
    series = sum(len(v) for v in series_por_ejercicio(jarvis, sesion["id"]).values())
    if series > 0:
        partes.append(str(series) + " series")
    minutos = sum(f["duracion_s"] for v in cardio_por_ejercicio(jarvis, sesion["id"]).values() for f in v) / 60
    if minutos > 0:
        partes.append(kg(round(minutos)) + " min de cardio")
    if len(partes) == 0:
        return "sesión empezada"
    return ", ".join(partes)
