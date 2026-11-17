"""Pantalla de agenda: pestanas Semana y Calendario.

Semana: rejilla con el horario (si el modulo horario esta activo) y, debajo,
las tareas de cada dia. Calendario: vista de mes para marcar dias importantes.

Solo presentacion: todo lo que guarda o calcula pasa por servicio.
Despues de guardar se hace st.rerun() para redibujar con los datos nuevos;
el mensaje viaja con nucleo.avisos.
"""

import calendar
from datetime import date, timedelta

import streamlit as st

from modulos.agenda import servicio
from nucleo import avisos
from nucleo.fechas import DIAS_CORTOS, DIAS_SEMANA, MESES, a_fecha, dia_bonito, lunes_de

ESTADO_TEXTO = {"pendiente": "Pendiente", "en_curso": "En curso", "hecha": "Hecha", "cancelada": "Cancelada"}
TIPO_TEXTO = {"clase": "Clase", "trabajo": "Trabajo", "otro": "Otro"}


def dibujar(jarvis, modulo):
    st.title(modulo.titulo)
    semana, calendario_ = st.tabs(["Semana", "Calendario"])
    with semana:
        pestana_semana(jarvis)
    with calendario_:
        pestana_calendario(jarvis)


def _guardado(texto):
    avisos.avisar("exito", texto)
    st.rerun()


# ======================================================================
# Semana
# ======================================================================
def tarjeta_bloque(bloque):
    with st.container(border=True):
        horas = "**" + bloque["hora_inicio"] + "–" + bloque["hora_fin"] + "**"
        if bloque["cancelado"]:
            st.markdown("~~" + horas + "~~  \n~~" + bloque["titulo"] + "~~")
            st.caption("Cancelado" + _con_motivo(bloque["motivo"]))
            return
        st.markdown(horas + "  \n" + bloque["titulo"])
        trozos = [TIPO_TEXTO[bloque["tipo"]]]
        if bloque["ubicacion"]:
            trozos.append(bloque["ubicacion"])
        if bloque["modificado"]:
            trozos.append("cambio de hora" + _con_motivo(bloque["motivo"]))
        st.caption(" · ".join(trozos))


def _con_motivo(motivo):
    if motivo:
        return ": " + motivo
    return ""


def _marcar(jarvis, tarea_id, clave):
    """Callback de la casilla: se ejecuta antes de redibujar."""
    estado = "pendiente"
    if st.session_state[clave]:
        estado = "hecha"
    servicio.cambiar_estado(jarvis, tarea_id, estado)


def casilla_tarea(jarvis, tarea):
    # El estado va en la clave para que la casilla se recree si cambia desde el menu Editar.
    clave = "hecha_" + str(tarea["id"]) + "_" + tarea["estado"]
    texto = tarea["titulo"]
    if tarea["estado"] in ("hecha", "cancelada"):
        texto = "~~" + texto + "~~"
    # Casilla y texto por separado: la etiqueta de una casilla se corta en columnas estrechas.
    col_casilla, col_texto = st.columns([0.2, 0.8], gap="small")
    col_casilla.checkbox(
        texto, value=tarea["estado"] == "hecha", key=clave, label_visibility="collapsed",
        on_change=_marcar, args=(jarvis, tarea["id"], clave),
        disabled=tarea["estado"] == "cancelada",
    )
    col_texto.markdown(texto)


def _anadir(jarvis, dia, clave):
    """Callback del campo Nueva tarea: se dispara al pulsar Enter."""
    titulo = st.session_state[clave]
    if titulo.strip() == "":
        return
    servicio.crear_tarea(jarvis, titulo, fecha=dia)
    st.session_state[clave] = ""


def nueva_tarea(jarvis, dia):
    clave = "nueva_tarea_" + dia
    st.text_input(
        "Nueva tarea", key=clave, label_visibility="collapsed", placeholder="+ Nueva tarea",
        on_change=_anadir, args=(jarvis, dia, clave),
    )


def editar_tareas_del_dia(jarvis, dia, tareas):
    """Menu para cambiar o borrar una tarea del dia."""
    por_id = {}
    for tarea in tareas:
        por_id[tarea["id"]] = tarea
    tarea_id = st.selectbox(
        "Tarea", list(por_id), format_func=lambda i: por_id[i]["titulo"], key="editar_elegida_" + dia,
    )
    tarea = por_id[tarea_id]
    with st.form("editar_tarea_" + dia + "_" + str(tarea_id)):
        titulo = st.text_input("Título", value=tarea["titulo"])
        nuevo_dia = st.date_input("Día", value=a_fecha(tarea["fecha"]), format="DD/MM/YYYY")
        estado = st.selectbox(
            "Estado", list(servicio.ESTADOS),
            index=servicio.ESTADOS.index(tarea["estado"]), format_func=ESTADO_TEXTO.get,
        )
        guardar = st.form_submit_button("Guardar", type="primary")
    if guardar:
        try:
            servicio.editar_tarea(
                jarvis, tarea_id, titulo, tarea["descripcion"], nuevo_dia,
                tarea["fecha_limite"], tarea["prioridad"], estado,
            )
            _guardado("Tarea actualizada")
        except ValueError as error:
            st.error(str(error))
    if st.button("Borrar tarea", key="borrar_tarea_" + str(tarea_id)):
        servicio.borrar_tarea(jarvis, tarea_id)
        _guardado("Tarea borrada")


def cabecera_dia(jarvis, dia, importantes):
    texto = "**" + dia_bonito(dia) + "**"
    if dia == jarvis.fecha_activa:
        texto = ":blue[" + texto + "]"
    st.markdown(texto)
    if dia in importantes:
        st.markdown(":red[" + (importantes[dia] or "Día importante") + "]")


def pestana_semana(jarvis):
    selector, _ = st.columns([0.25, 0.75])
    elegido = selector.date_input(
        "Semana del", value=a_fecha(jarvis.fecha_activa), format="DD/MM/YYYY", key="agenda_semana",
    )
    lunes = lunes_de(elegido)
    domingo = lunes + timedelta(days=6)
    importantes = servicio.dias_importantes(jarvis, lunes, domingo)

    # --- Horario ---
    horario = servicio.horario_de_semana(jarvis, lunes)
    columnas = st.columns(7)
    for i, columna in enumerate(columnas):
        dia = (lunes + timedelta(days=i)).isoformat()
        with columna:
            cabecera_dia(jarvis, dia, importantes)
            if horario is None:
                continue
            if len(horario[dia]) == 0:
                st.caption("Libre")
            for bloque in horario[dia]:
                tarjeta_bloque(bloque)
    if horario is None:
        st.caption("El módulo Horario está desactivado; actívalo en Ajustes para ver aquí tus clases y turnos.")

    # --- Tareas ---
    st.subheader("Tareas")
    tareas = servicio.tareas_de_semana(jarvis, lunes)
    columnas = st.columns(7)
    for columna, (dia, lista) in zip(columnas, tareas.items()):
        with columna:
            st.caption(DIAS_CORTOS[a_fecha(dia).weekday()])
            for tarea in lista:
                casilla_tarea(jarvis, tarea)
            nueva_tarea(jarvis, dia)
            if len(lista) > 0:
                with st.popover("Editar", width="stretch"):
                    editar_tareas_del_dia(jarvis, dia, lista)


# ======================================================================
# Calendario
# ======================================================================
CLAVE_MES = "agenda_mes"
CLAVE_DIA = "agenda_dia_elegido"


def _mover_mes(pasos):
    primero = st.session_state[CLAVE_MES]
    mes = primero.month - 1 + pasos
    st.session_state[CLAVE_MES] = date(primero.year + mes // 12, mes % 12 + 1, 1)


def _elegir_dia(dia):
    st.session_state[CLAVE_DIA] = dia


def pestana_calendario(jarvis):
    activa = a_fecha(jarvis.fecha_activa)
    if CLAVE_MES not in st.session_state:
        st.session_state[CLAVE_MES] = activa.replace(day=1)
    if CLAVE_DIA not in st.session_state:
        st.session_state[CLAVE_DIA] = jarvis.fecha_activa
    primero = st.session_state[CLAVE_MES]

    anterior, titulo, siguiente = st.columns([0.15, 0.70, 0.15], vertical_alignment="center")
    anterior.button("Anterior", on_click=_mover_mes, args=(-1,), width="stretch")
    titulo.markdown("#### " + MESES[primero.month - 1] + " " + str(primero.year))
    siguiente.button("Siguiente", on_click=_mover_mes, args=(1,), width="stretch")

    semanas = calendar.Calendar(firstweekday=0).monthdatescalendar(primero.year, primero.month)
    importantes = servicio.dias_importantes(jarvis, semanas[0][0], semanas[-1][-1])

    cabeceras = st.columns(7)
    for i, columna in enumerate(cabeceras):
        columna.caption(DIAS_CORTOS[i])
    for semana in semanas:
        columnas = st.columns(7)
        for columna, dia in zip(columnas, semana):
            with columna:
                celda_dia(jarvis, dia, primero.month, importantes)

    st.divider()
    panel_dia(jarvis, st.session_state[CLAVE_DIA], importantes)


def celda_dia(jarvis, dia, mes, importantes):
    if dia.month != mes:
        st.write("")
        return
    texto = dia.isoformat()
    etiqueta = str(dia.day)
    if texto == jarvis.fecha_activa:
        etiqueta = "**" + etiqueta + "** · hoy"
    tipo = "secondary"
    if texto in importantes:
        tipo = "primary"
    st.button(
        etiqueta, key="cal_" + texto, type=tipo, width="stretch",
        on_click=_elegir_dia, args=(texto,),
    )
    if texto in importantes and importantes[texto]:
        st.caption(importantes[texto])


def panel_dia(jarvis, dia, importantes):
    fecha = a_fecha(dia)
    st.markdown("**" + DIAS_SEMANA[fecha.weekday()] + " " + str(fecha.day) + " de " + MESES[fecha.month - 1].lower() + "**")
    # Los dias importantes del dia elegido pueden no estar en el mes visible.
    if dia not in importantes:
        importantes = servicio.dias_importantes(jarvis, dia, dia)
    marcado = dia in importantes
    with st.form("dia_importante_" + dia):
        importante = st.checkbox("Día importante", value=marcado)
        nota = st.text_input("Nota", value=importantes.get(dia, ""), placeholder="Examen de Cálculo, entrega…")
        guardar = st.form_submit_button("Guardar", type="primary")
    if guardar:
        if importante:
            servicio.marcar_importante(jarvis, dia, nota)
            _guardado("Día marcado")
        elif marcado:
            servicio.desmarcar_importante(jarvis, dia)
            _guardado("Día desmarcado")
