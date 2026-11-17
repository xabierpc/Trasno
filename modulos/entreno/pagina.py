"""Pantalla de entreno: pestanas Entreno, Rutina, PR e Historial.

Solo presentacion: todo lo que guarda o calcula pasa por servicio.
Despues de guardar se hace st.rerun(); el mensaje viaja con nucleo.avisos.
"""

from datetime import date

import pandas as pd
import streamlit as st

from modulos.entreno import servicio
from modulos.entreno.servicio import kg
from nucleo import avisos
from nucleo.fechas import DIAS_SEMANA, a_fecha, dia_bonito

TIPO_TEXTO = {"fuerza": "Fuerza", "cardio": "Cardio"}


def dibujar(jarvis, modulo):
    st.title(modulo.titulo)
    entreno, rutina, prs, historial = st.tabs(["Entreno", "Rutina", "PR", "Historial"])
    with entreno:
        pestana_entreno(jarvis)
    with rutina:
        pestana_rutina(jarvis)
    with prs:
        pestana_prs(jarvis)
    with historial:
        pestana_historial(jarvis)


def _hecho(texto, tipo="exito"):
    avisos.avisar(tipo, texto)
    st.rerun()


# ======================================================================
# Entreno (registro siguiendo la rutina)
# ======================================================================
def pestana_entreno(jarvis):
    selector, _ = st.columns([0.25, 0.75])
    dia = selector.date_input("Día", value=a_fecha(jarvis.fecha_activa), format="DD/MM/YYYY", key="entreno_dia")
    fecha = dia.isoformat()
    plan = servicio.plan_de(jarvis, fecha)
    sesion = servicio.sesion_de(jarvis, fecha)

    if plan is not None:
        st.subheader(plan["dia"]["nombre"])
        st.caption("Rutina " + plan["rutina"]["nombre"] + " · " + DIAS_SEMANA[dia.weekday()])
    elif servicio.rutina_activa(jarvis) is None:
        st.info("Todavía no tienes rutina. Créala en la pestaña Rutina; mientras, puedes entrenar igualmente.")
    else:
        st.subheader("Descanso")
        st.caption("Tu rutina no tiene entreno este día.")

    if sesion is None:
        texto = "Empezar entreno"
        if plan is None:
            texto = "Entrenar igualmente"
        if st.button(texto, type="primary", key="empezar_" + fecha):
            servicio.empezar_sesion(jarvis, fecha)
            st.rerun()
        return

    sesion_id = sesion["id"]
    series = servicio.series_por_ejercicio(jarvis, sesion_id)
    cardio = servicio.cardio_por_ejercicio(jarvis, sesion_id)

    # Ejercicios a mostrar: los del plan en su orden, luego los extra (con datos o recien anadidos).
    lista = []
    vistos = set()
    if plan is not None:
        for fila in plan["ejercicios"]:
            if fila["ejercicio_id"] not in vistos:
                lista.append((fila["ejercicio_id"], fila))
                vistos.add(fila["ejercicio_id"])
    clave_extras = "entreno_extras_" + fecha
    extras = list(series) + list(cardio) + st.session_state.get(clave_extras, [])
    for ejercicio_id in extras:
        if ejercicio_id not in vistos:
            lista.append((ejercicio_id, None))
            vistos.add(ejercicio_id)

    por_id = {}
    for ejercicio in servicio.ejercicios(jarvis):
        por_id[ejercicio["id"]] = ejercicio

    for ejercicio_id, objetivo in lista:
        ejercicio = por_id.get(ejercicio_id)
        if ejercicio is None:
            continue
        with st.container(border=True):
            if ejercicio["tipo"] == "fuerza":
                bloque_fuerza(jarvis, sesion_id, ejercicio, objetivo, series.get(ejercicio_id, []), fecha)
            else:
                bloque_cardio(jarvis, sesion_id, ejercicio, objetivo, cardio.get(ejercicio_id, []), fecha)

    # Ejercicio fuera de la rutina
    disponibles = [e for e in por_id.values() if e["id"] not in vistos]
    if disponibles:
        col_sel, col_boton = st.columns([0.75, 0.25], vertical_alignment="bottom")
        elegido = col_sel.selectbox(
            "Añadir ejercicio fuera de la rutina", [e["id"] for e in disponibles],
            format_func=lambda i: por_id[i]["nombre"], key="extra_sel_" + fecha,
        )
        if col_boton.button("Añadir ejercicio", key="extra_btn_" + fecha, width="stretch"):
            st.session_state[clave_extras] = st.session_state.get(clave_extras, []) + [elegido]
            st.rerun()

    with st.expander("Notas y opciones de la sesión"):
        with st.form("notas_" + fecha):
            notas = st.text_area("Notas", value=sesion["notas"] or "", placeholder="Cómo te has sentido, molestias…")
            if st.form_submit_button("Guardar notas"):
                servicio.guardar_notas(jarvis, sesion_id, notas)
                _hecho("Notas guardadas")
        if st.button("Borrar el entreno de este día", key="borrar_sesion_" + fecha,
                     help="Borra la sesión con todas sus series y cardio."):
            servicio.borrar_sesion(jarvis, sesion_id)
            st.session_state.pop(clave_extras, None)
            _hecho("Entreno borrado")


def _cabecera_ejercicio(ejercicio, objetivo):
    texto = "**" + ejercicio["nombre"] + "**"
    if objetivo is not None:
        meta = servicio.objetivo_texto(objetivo)
        if meta:
            texto = texto + " · objetivo " + meta
    else:
        texto = texto + " · fuera de la rutina"
    st.markdown(texto)


def bloque_fuerza(jarvis, sesion_id, ejercicio, objetivo, series, fecha):
    _cabecera_ejercicio(ejercicio, objetivo)
    for serie in series:
        col_texto, col_boton = st.columns([0.85, 0.15], vertical_alignment="center")
        texto = str(serie["orden"]) + ".  " + str(serie["reps"]) + " × " + kg(serie["peso_kg"]) + " kg"
        if serie["rpe"] is not None:
            texto = texto + "  · RPE " + kg(serie["rpe"])
        col_texto.markdown(texto)
        if col_boton.button("Quitar", key="quitar_serie_" + str(serie["id"]), width="stretch"):
            servicio.borrar_serie(jarvis, serie["id"])
            st.rerun()

    # Valores por defecto: la ultima serie hecha, si no el objetivo.
    reps_def = 5
    peso_def = 0.0
    if objetivo is not None:
        reps_def = objetivo["reps_objetivo"] or reps_def
        peso_def = float(objetivo["peso_objetivo_kg"] or peso_def)
    if series:
        reps_def = series[-1]["reps"]
        peso_def = float(series[-1]["peso_kg"])

    base = "serie_" + fecha + "_" + str(ejercicio["id"])
    col_reps, col_peso, col_rpe, col_boton = st.columns([0.2, 0.3, 0.2, 0.3], vertical_alignment="bottom")
    reps = col_reps.number_input("Reps", min_value=1, step=1, value=int(reps_def), key=base + "_reps")
    peso = col_peso.number_input("Peso (kg)", min_value=0.0, step=2.5, value=peso_def, key=base + "_peso")
    rpe = col_rpe.number_input("RPE", min_value=1.0, max_value=10.0, step=0.5, value=None, key=base + "_rpe",
                               help="Opcional")
    if col_boton.button("Añadir serie", key=base + "_btn", width="stretch", type="primary"):
        try:
            pr = servicio.anadir_serie(jarvis, sesion_id, ejercicio["id"], reps, peso, rpe)
            if pr is not None:
                avisos.avisar("exito", pr)
            st.rerun()
        except ValueError as error:
            st.error(str(error))


def bloque_cardio(jarvis, sesion_id, ejercicio, objetivo, registros, fecha):
    _cabecera_ejercicio(ejercicio, objetivo)
    for fila in registros:
        col_texto, col_boton = st.columns([0.85, 0.15], vertical_alignment="center")
        texto = kg(round(fila["duracion_s"] / 60, 1)) + " min"
        if fila["distancia_m"]:
            texto = texto + " · " + kg(round(fila["distancia_m"] / 1000, 2)) + " km"
        if fila["notas"]:
            texto = texto + " · " + fila["notas"]
        col_texto.markdown(texto)
        if col_boton.button("Quitar", key="quitar_cardio_" + str(fila["id"]), width="stretch"):
            servicio.borrar_cardio(jarvis, fila["id"])
            st.rerun()

    min_def = 30.0
    km_def = None
    if objetivo is not None:
        if objetivo["duracion_objetivo_s"]:
            min_def = objetivo["duracion_objetivo_s"] / 60
        if objetivo["distancia_objetivo_m"]:
            km_def = objetivo["distancia_objetivo_m"] / 1000

    base = "cardio_" + fecha + "_" + str(ejercicio["id"])
    col_min, col_km, col_boton = st.columns([0.3, 0.3, 0.4], vertical_alignment="bottom")
    minutos = col_min.number_input("Minutos", min_value=0.0, step=1.0, value=float(min_def), key=base + "_min")
    km_ = col_km.number_input("Km", min_value=0.0, step=0.1, value=km_def, key=base + "_km", help="Opcional")
    if col_boton.button("Añadir", key=base + "_btn", width="stretch", type="primary"):
        try:
            servicio.anadir_cardio(jarvis, sesion_id, ejercicio["id"], minutos, km_)
            st.rerun()
        except ValueError as error:
            st.error(str(error))


# ======================================================================
# Rutina
# ======================================================================
def pestana_rutina(jarvis):
    lista = servicio.rutinas(jarvis)

    with st.expander("Nueva rutina", expanded=len(lista) == 0):
        with st.form("nueva_rutina", clear_on_submit=True, border=False):
            nombre = st.text_input("Nombre", placeholder="PPL, Torso-pierna, Full body…")
            if st.form_submit_button("Crear rutina", type="primary"):
                try:
                    servicio.crear_rutina(jarvis, nombre)
                    _hecho("Rutina creada")
                except ValueError as error:
                    st.error(str(error))

    with st.expander("Ejercicios"):
        catalogo_ejercicios(jarvis)

    if len(lista) == 0:
        return

    por_id = {}
    for rutina in lista:
        por_id[rutina["id"]] = rutina

    def nombre_rutina(rutina_id):
        texto = por_id[rutina_id]["nombre"]
        if por_id[rutina_id]["activa"]:
            texto = texto + " (activa)"
        return texto

    col_sel, col_activar, col_borrar = st.columns([0.6, 0.2, 0.2], vertical_alignment="bottom")
    rutina_id = col_sel.selectbox("Rutina", list(por_id), format_func=nombre_rutina, key="rutina_elegida")
    rutina = por_id[rutina_id]
    if col_activar.button("Usar esta", disabled=rutina["activa"] == 1, width="stretch",
                          help="La rutina activa es la que se sigue en la pestaña Entreno."):
        servicio.activar_rutina(jarvis, rutina_id)
        _hecho("Ahora sigues «" + rutina["nombre"] + "»")
    with col_borrar.popover("Borrar", width="stretch"):
        st.write("Se borra el plan. Los entrenos que ya apuntaste se conservan.")
        if st.button("Borrar «" + rutina["nombre"] + "»", key="borrar_rutina_" + str(rutina_id)):
            servicio.borrar_rutina(jarvis, rutina_id)
            _hecho("Rutina borrada")

    dias = servicio.dias_de_rutina(jarvis, rutina_id)
    for dia_semana in range(7):
        dia = dias.get(dia_semana)
        titulo = DIAS_SEMANA[dia_semana] + " · "
        if dia is None:
            titulo = titulo + "descanso"
        else:
            titulo = titulo + dia["nombre"]
        with st.expander(titulo):
            editor_dia(jarvis, rutina_id, dia_semana, dia)


def editor_dia(jarvis, rutina_id, dia_semana, dia):
    base = "rd_" + str(rutina_id) + "_" + str(dia_semana)
    col_nombre, col_guardar, col_quitar = st.columns([0.6, 0.2, 0.2], vertical_alignment="bottom")
    valor = ""
    if dia is not None:
        valor = dia["nombre"]
    nombre = col_nombre.text_input("Nombre del día", value=valor, key=base + "_nombre",
                                   placeholder="Pierna, Empuje, Tirón…")
    texto_guardar = "Guardar nombre"
    if dia is None:
        texto_guardar = "Entrenar este día"
    if col_guardar.button(texto_guardar, key=base + "_guardar", width="stretch"):
        try:
            servicio.guardar_dia(jarvis, rutina_id, dia_semana, nombre)
            _hecho("Día guardado")
        except ValueError as error:
            st.error(str(error))
    if dia is None:
        return
    if col_quitar.button("Hacer descanso", key=base + "_quitar", width="stretch",
                         help="Quita el día y sus ejercicios del plan."):
        servicio.quitar_dia(jarvis, dia["id"])
        _hecho("Ahora es día de descanso")

    for fila in servicio.ejercicios_de_dia(jarvis, dia["id"]):
        col_texto, col_boton = st.columns([0.85, 0.15], vertical_alignment="center")
        texto = str(fila["orden"]) + ". **" + fila["nombre"] + "**"
        meta = servicio.objetivo_texto(fila)
        if meta:
            texto = texto + " · " + meta
        col_texto.markdown(texto)
        if col_boton.button("Quitar", key="quitar_re_" + str(fila["id"]), width="stretch"):
            servicio.quitar_de_dia(jarvis, fila["id"])
            st.rerun()

    # Anadir ejercicio al dia (sin st.form: los campos cambian segun sea fuerza o cardio)
    catalogo = servicio.ejercicios(jarvis)
    por_id = {}
    for ejercicio in catalogo:
        por_id[ejercicio["id"]] = ejercicio
    ejercicio_id = st.selectbox(
        "Añadir ejercicio", list(por_id), key=base + "_ej",
        format_func=lambda i: por_id[i]["nombre"] + " (" + por_id[i]["tipo"] + ")",
    )
    if por_id[ejercicio_id]["tipo"] == "fuerza":
        c1, c2, c3, c4 = st.columns([0.2, 0.2, 0.3, 0.3], vertical_alignment="bottom")
        series = c1.number_input("Series", min_value=0, step=1, value=3, key=base + "_series")
        reps = c2.number_input("Reps", min_value=0, step=1, value=8, key=base + "_reps")
        peso = c3.number_input("Peso (kg)", min_value=0.0, step=2.5, value=None, key=base + "_peso",
                               help="Opcional")
        if c4.button("Añadir al día", key=base + "_add", width="stretch", type="primary"):
            servicio.anadir_a_dia(jarvis, dia["id"], ejercicio_id, series=series, reps=reps, peso_kg=peso)
            st.rerun()
    else:
        c1, c2, c3 = st.columns([0.3, 0.3, 0.4], vertical_alignment="bottom")
        minutos = c1.number_input("Minutos", min_value=0.0, step=5.0, value=30.0, key=base + "_min")
        km_ = c2.number_input("Km", min_value=0.0, step=0.5, value=None, key=base + "_km", help="Opcional")
        if c3.button("Añadir al día", key=base + "_add", width="stretch", type="primary"):
            servicio.anadir_a_dia(jarvis, dia["id"], ejercicio_id, minutos=minutos, km=km_)
            st.rerun()


def catalogo_ejercicios(jarvis):
    with st.form("nuevo_ejercicio", clear_on_submit=True, border=False):
        c1, c2, c3 = st.columns([0.4, 0.25, 0.35])
        nombre = c1.text_input("Nombre", placeholder="Remo con barra, Cinta…")
        tipo = c2.selectbox("Tipo", list(servicio.TIPOS), format_func=TIPO_TEXTO.get)
        grupo = c3.text_input("Grupo muscular", placeholder="Opcional")
        if st.form_submit_button("Añadir ejercicio"):
            try:
                servicio.crear_ejercicio(jarvis, nombre, tipo, grupo)
                _hecho("Ejercicio añadido")
            except ValueError as error:
                st.error(str(error))

    for ejercicio in servicio.ejercicios(jarvis):
        col_texto, col_boton = st.columns([0.85, 0.15], vertical_alignment="center")
        texto = ejercicio["nombre"] + " · " + TIPO_TEXTO[ejercicio["tipo"]]
        if ejercicio["grupo_muscular"]:
            texto = texto + " · " + ejercicio["grupo_muscular"]
        col_texto.markdown(texto)
        if ejercicio["nombre"] in servicio.BASICOS:
            col_texto.caption("Básico")
            continue
        if col_boton.button("Borrar", key="borrar_ej_" + str(ejercicio["id"]), width="stretch"):
            try:
                servicio.borrar_ejercicio(jarvis, ejercicio["id"])
                _hecho("Ejercicio borrado")
            except ValueError as error:
                st.error(str(error))


# ======================================================================
# PR
# ======================================================================
def pestana_prs(jarvis):
    st.caption("PR a N reps = el mayor peso que has movido en una serie de N o más repeticiones. "
               "Salen de tus entrenos y de los PR que apuntes a mano.")
    basicos = servicio.basicos(jarvis)
    columnas = st.columns(3, gap="large")
    for columna, ejercicio in zip(columnas, basicos):
        with columna:
            tarjeta_pr(jarvis, ejercicio)

    st.subheader("Progreso")
    # Formato largo (una fila por dia y ejercicio): cada linea une solo sus propios puntos,
    # aunque los basicos se entrenen en dias distintos.
    puntos = []
    for ejercicio in basicos:
        for fila in servicio.progreso(jarvis, ejercicio["id"]):
            puntos.append({"Fecha": fila["fecha"], "Peso máximo (kg)": fila["peso_kg"], "Ejercicio": ejercicio["nombre"]})
    if len(puntos) == 0:
        st.caption("Cuando registres entrenos de los básicos verás aquí el peso máximo de cada día.")
    else:
        tabla = pd.DataFrame(puntos)
        tabla["Fecha"] = pd.to_datetime(tabla["Fecha"])
        st.line_chart(tabla, x="Fecha", y="Peso máximo (kg)", color="Ejercicio")

    st.subheader("PR apuntados a mano")
    formulario_pr_manual(jarvis, basicos)
    for pr in servicio.prs_manuales(jarvis):
        col_texto, col_boton = st.columns([0.85, 0.15], vertical_alignment="center")
        texto = "**" + pr["nombre"] + "** · " + kg(pr["peso_kg"]) + " kg × " + str(pr["reps"]) + " · " + _fecha_larga(pr["fecha"])
        if pr["notas"]:
            texto = texto + " · " + pr["notas"]
        col_texto.markdown(texto)
        if col_boton.button("Quitar", key="quitar_pr_" + str(pr["id"]), width="stretch"):
            servicio.borrar_pr_manual(jarvis, pr["id"])
            _hecho("PR quitado")


def _fecha_larga(texto):
    return a_fecha(texto).strftime("%d/%m/%Y")


def _fecha_corta(texto):
    return a_fecha(texto).strftime("%d/%m/%y")


def tarjeta_pr(jarvis, ejercicio):
    st.markdown("#### " + ejercicio["nombre"])
    tabla = servicio.tabla_prs(jarvis, ejercicio["id"])
    uno = tabla[0]["marca"]
    if uno is None:
        st.metric("1RM", "—")
    else:
        st.metric("1RM", kg(uno["peso_kg"]) + " kg")
    filas = []
    for fila in tabla:
        marca = fila["marca"]
        if marca is None:
            filas.append({"Reps": fila["reps"], "Peso": "—", "Hecho": "", "Fecha": ""})
            continue
        hecho = kg(marca["peso_kg"]) + " × " + str(marca["reps"])
        if marca["origen"] == "manual":
            hecho = hecho + " *"
        filas.append({"Reps": fila["reps"], "Peso": kg(marca["peso_kg"]) + " kg", "Hecho": hecho,
                      "Fecha": _fecha_corta(marca["fecha"])})
    st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch")
    if any(f["marca"] is not None and f["marca"]["origen"] == "manual" for f in tabla):
        st.caption("\\* apuntado a mano")


def formulario_pr_manual(jarvis, basicos):
    por_id = {}
    for ejercicio in basicos:
        por_id[ejercicio["id"]] = ejercicio
    with st.form("pr_manual", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns([0.3, 0.25, 0.2, 0.25])
        ejercicio_id = c1.selectbox("Ejercicio", list(por_id), format_func=lambda i: por_id[i]["nombre"])
        fecha = c2.date_input("Fecha", value=date.today(), max_value=date.today(), format="DD/MM/YYYY")
        reps = c3.number_input("Reps", min_value=1, step=1, value=1)
        peso = c4.number_input("Peso (kg)", min_value=0.0, step=2.5, value=None)
        notas = st.text_input("Notas", placeholder="Opcional: competición, con cinturón…")
        if st.form_submit_button("Apuntar PR", type="primary"):
            try:
                servicio.anadir_pr_manual(jarvis, ejercicio_id, fecha, reps, peso, notas)
                _hecho("PR apuntado")
            except ValueError as error:
                st.error(str(error))


# ======================================================================
# Historial
# ======================================================================
def pestana_historial(jarvis):
    filas = servicio.historial(jarvis)
    if len(filas) == 0:
        st.info("Todavía no hay entrenos registrados.")
        return
    tabla = []
    for fila in filas:
        cardio = ""
        if fila["cardio_s"]:
            cardio = kg(round(fila["cardio_s"] / 60)) + " min"
            if fila["cardio_m"]:
                cardio = cardio + " · " + kg(round(fila["cardio_m"] / 1000, 2)) + " km"
        tabla.append({
            "Día": dia_bonito(fila["fecha"]) + " " + fila["fecha"][:4],
            "Entreno": fila["dia"] or "Libre",
            "Series": fila["series"],
            "Volumen (kg)": int(round(fila["volumen"])),
            "Cardio": cardio,
            "Notas": fila["notas"] or "",
        })
    st.dataframe(pd.DataFrame(tabla), hide_index=True, width="stretch")
    st.caption("Para ver o corregir un día, elígelo en la pestaña Entreno.")
