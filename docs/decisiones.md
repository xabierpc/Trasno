# Decisiones

Registro de decisiones de diseño. Una entrada por decisión: fecha, decisión y motivo.

## 2026-11-14 · Ventana de madrugada: 00:00-06:00

Los registros con timestamp entre las 00:00 y las 06:00 (hora de `Europe/Madrid`) son ambiguos: se pregunta al usuario a qué día lógico cuentan. Es configurable en `Settings.ventana_madrugada`.

**Motivo:** acostarse tarde no debe hacer que un entreno o una métrica caiga en el día siguiente sin querer.

## 2026-11-14 · Log del agente en `core.sqlite`

Cada herramienta que usa el agente se registra en una tabla de `core.sqlite`, no en una base de datos propia del agente.

**Motivo:** el log es transversal (registra acciones sobre cualquier módulo) y lo consulta el core; así hay un único sitio para auditar lo que hizo el agente.

## 2026-11-14 · Usuario único creado en la migración inicial

La migración `0001` de core crea el usuario `id=1` (nombre `usuario`), que coincide con `Settings.user_id` por defecto. Todas las tablas apuntan a `user.id` con `ON DELETE CASCADE`.

**Motivo:** hoy hay un solo usuario, pero las tablas ya llevan `user_id` para poder tener varios sin migrar datos.

## 2026-11-14 · Timestamps en UTC con `TZDateTime`

SQLite no guarda zonas horarias. `core.db.TZDateTime` convierte a UTC al guardar, devuelve datetimes UTC con zona al leer y rechaza datetimes sin zona. La `logical_date` va en una columna aparte (regla 5).

**Motivo:** comparar y ordenar instantes de forma correcta; la hora local se calcula al mostrar con `Settings.timezone`.

## 2026-11-14 · Datos de arranque por convención de fichero

`trasno migrate` aplica `upgrade head` al core y a cada `modules/<m>/infrastructure/migrations/` (si tiene `env.py`) sobre `data/<m>.sqlite`. Después, si existe `modules/<m>/infrastructure/arranque.py`, llama a su `datos_arranque(engine) -> None`. Se ejecuta en cada migrate, así que debe ser idempotente (`INSERT ... ON CONFLICT DO NOTHING` o comprobar antes). El `env.py` de cada módulo se reduce a `ejecutar_env(Base.metadata, "<m>")` de `core.migraciones`.

**Motivo:** un módulo nuevo se migra sin tocar el core ni `contracts.py`, y migrar no exige cargar los módulos ni montar el `AppContext`.

## 2026-11-14 · Representación de los valores de tracking

Duración en **minutos enteros**; booleana como `bool` estricto (se guardará 0/1 y así sale como serie y sirve para rachas); escala y conteo como `int`; numérica como `float`; categórica como texto, **sin serie numérica** en analytics de momento. Una categórica solo admite agregación `ultima` y no tiene objetivo.

**Motivo:** encaja directamente con SQLite y con `SeriesProvider` (valores `float`); la categórica es la única que no tiene una lectura numérica obvia y se deja para cuando haga falta.

## 2026-11-14 · Ventana de madrugada como helper del dominio de tracking

`modules/tracking/domain/fecha_logica.py` ofrece `es_madrugada(instante, ventana, zona)` y `opciones_fecha_logica(instante, zona) -> (ayer, hoy)`. No eligen la fecha: la `logical_date` sigue siendo obligatoria en los casos de uso. La ventana puede cruzar la medianoche.

**Motivo:** la página de Streamlit y el agente necesitan la misma regla para saber cuándo preguntar; así no se duplica.

## 2026-11-14 · Repositorios de tracking ligados al usuario y con commit por operación

Los ports (`application/ports.py`) no reciben `user_id`: cada repositorio se construye ya ligado a un usuario y filtra todas sus consultas por él. Los repositorios SQL abren una sesión por operación y hacen commit al terminar. `guardar(entrada)` es un upsert por `(metric_id, logical_date, slot)` que conserva el `id` de la entrada que ya existía.

**Motivo:** los casos de uso quedan con firmas limpias para el agente (regla 11) y, como el dato ya está guardado cuando el repositorio devuelve, el evento `MetricaRegistrada` se publica después del commit sin necesidad de compartir la sesión.

## 2026-11-14 · `replace` usa el slot 0 y `keep_all` el siguiente libre

Con `on_duplicate=replace` la entrada va siempre al slot 0 (el segundo registro del día pisa valor y timestamp). Con `keep_all` va a `max(slot) + 1`, así que tras un borrado no se reutiliza un slot intermedio.

## 2026-11-14 · Columnas de valor: `valor_num` y `valor_texto`

`metric_entry` guarda el valor en `valor_num` (numérica, duración, escala, conteo y booleana como 0/1) o en `valor_texto` (categórica); un CHECK obliga a que haya exactamente una. El tipo de la métrica decide cómo se reconstruye al leer. `user_id` no lleva FK porque `user` vive en `core.sqlite`, otro fichero.

## 2026-11-14 · API de tracking

Rutas: `POST/GET /tracking/metrics`, `POST/GET /tracking/entries`, `DELETE /tracking/entries/{id}` y `GET /tracking/fecha-logica` (`{es_madrugada, ayer, hoy}`). `logical_date` es obligatoria al registrar: quien llama (página o agente) pregunta antes si es madrugada. Errores de dominio → HTTP: no encontrado 404, métrica duplicada 409 y el resto 422, con `{"detail": "..."}`. El router vive en `modules/tracking/api.py` y lo crea `crear_router(casos, settings)`.

**Motivo:** `/tracking/fecha-logica` evita que la página de Streamlit tenga la regla de la madrugada (regla 9).

## 2026-11-14 · Series de tracking

Cada métrica no categórica es una serie con el mismo nombre que la métrica (`peso`). Devuelve un valor por día lógico según su agregación (`suma`, `media` o `ultima` = el slot más alto).

## 2026-11-14 · Media móvil del peso calculada en el dashboard

`interfaces/dashboard/graficas.py` calcula la media móvil de 7 días con una ventana por tiempo (los días sin registro no la alargan). Es presentación; cuando haga falta en el briefing o el agente se usará la de `analytics`.

## 2026-11-14 · Métricas de arranque de T1

Además de `peso`: `pasos` (conteo, suma, objetivo 8 000), `sueño` (duración en minutos, objetivo 420 = 7 h), `ánimo` y `energía` (escala 1-10, media) y los hábitos booleanos `leer`, `estudiar`, `meditar`, `estirar` y `entrenar`. Todas `replace`: se apunta el total del día.

## 2026-11-14 · Rachas y cumplimiento

Se calculan al pedirlos (`domain/rachas.py`), nunca se guardan. Un día está cumplido según la métrica: booleana → `true`; con objetivo → valor agregado del día ≥ objetivo; sin objetivo → basta con haber registrado. **Hoy nunca rompe la racha**: si aún no está cumplido se cuenta hasta ayer. El cumplimiento semanal y mensual son ventanas móviles de 7 y 30 días que terminan hoy (no semana ni mes naturales), siempre sobre 7 y 30. `racha(nombre, hoy)` exige `hoy`, igual que el resto de casos de uso exige la fecha lógica; la API lo deduce del reloj si no llega.

**Motivo:** con semana natural el lunes siempre saldría «1/1»; la ventana móvil es estable y comparable de un día a otro.

## 2026-11-14 · Métricas activas

`metric_definition.activa` (migración 0002, por defecto `true`). Desactivar una métrica la quita del «Registro diario» pero conserva sus entradas y su serie. `GET /tracking/metrics?activas=true` filtra y `PATCH /tracking/metrics/{nombre}` cambia el estado.

La migración usa `op.add_column` directo y **no** `batch_alter_table`: el modo batch recrea la tabla y, con `foreign_keys=ON`, al borrar la antigua el `ON DELETE CASCADE` se lleva todas las entradas. Regla para el futuro: nunca batch sobre una tabla que tenga hijas con cascada (o desactivar las FK durante esa migración). Hay un test de regresión que migra de 0001 a head con datos.

## 2026-11-14 · Página «Registro diario»

Un campo por métrica activa según su tipo; la duración se escribe en horas y se guarda en minutos. Los campos arrancan con lo registrado ese día y al guardar solo se envía lo que ha cambiado; un hábito sin marcar y sin registro previo no se envía (queda «sin registrar», no `false`). Las métricas `keep_all` empiezan vacías porque cada guardado añade una lectura. `pedir_fecha` pasa a `interfaces/dashboard/fecha.py` para compartirla entre páginas.

## 2026-11-14 · Modelo de training

`training.sqlite` con tres tablas: `sesion` → `ejercicio` → `serie` (FK con `ON DELETE CASCADE`, `orden` único dentro del padre). La sesión lleva `logical_date`, `tipo` (**texto libre**, guardado en minúsculas), `duracion_min` y `energia_previa` (1-10), los dos últimos opcionales. Una sesión sin ejercicios es válida (cardio). El peso de una serie puede ser 0 (peso corporal) y el RPE admite medios (1-10).

Los nombres de ejercicio se normalizan en el dominio (minúsculas y un solo espacio): «Press  Banca» y «press banca» son el mismo ejercicio. No hay catálogo de ejercicios: existen los que aparecen en alguna sesión.

**Motivo:** un catálogo obligaría a darlos de alta antes de entrenar; normalizar el nombre basta para que el progreso no se parta en dos.

## 2026-11-14 · Cálculos de training

Nada derivado se guarda. 1RM estimado con **Epley** (`peso · (1 + reps/30)`; con 1 repetición es el propio peso). Volumen = Σ reps · peso. El progreso de un ejercicio da un punto por día lógico: mejor 1RM, peso máximo y volumen del día. Récords personales por ejercicio: peso, 1RM estimado y volumen en un día; en un empate cuenta el primer día. `registrar_sesion` devuelve los récords que la sesión bate respecto a las sesiones de fecha anterior o igual; la primera vez que se hace un ejercicio no cuenta como récord.

## 2026-11-14 · API y series de training

Rutas: `POST/GET /training/sessions`, `DELETE /training/sessions/{id}`, `GET /training/exercises`, `GET /training/exercises/{nombre}/progress`, `GET /training/records` y `GET /training/weekly-volume`. Eventos: `SesionRegistrada` y `SesionBorrada`. Series para analytics: `volumen_semanal` (un punto por semana, fechado en su lunes; solo semanas cuyo lunes cae en el rango, siempre completas) y `1rm <ejercicio>` (mejor 1RM estimado de cada día).

**Motivo:** las claves de serie son globales en analytics; el prefijo `1rm ` evita chocar con una métrica de tracking que se llame igual que un ejercicio.

## 2026-11-14 · Página «Entrenos»

Cada fila del formulario son N series iguales de un ejercicio (ejercicio · series · reps · peso · RPE), con 3 series por defecto; las filas del mismo ejercicio se juntan y un peso vacío cuenta como 0 (peso corporal). El ejercicio se elige de los ya registrados o se escribe uno nuevo. Tras guardar, el formulario se vacía y se avisa de los récords batidos. La fecha lógica se pide a `GET /tracking/fecha-logica`: la página es un cliente de la API, así que training no duplica la regla de la madrugada ni importa a tracking. Agrupar filas vive en `interfaces/dashboard/entrenos.py` (presentación); validar valores sigue siendo cosa del dominio.

## 2026-11-14 · Dominio de planning

Tres entidades: `Tarea` (título, día lógico opcional, prioridad `baja`/`media`/`alta`, estimación en minutos, estado `pendiente`/`hecha` con `hecha_en`), `Evento` (intervalo concreto con zona horaria; origen `manual` o `ics`, y los del `.ics` llevan `uid_externo` para no duplicarse al reimportar) y `BloqueRecurrente` (semanal, en hora local, con periodo `desde`/`hasta` opcional). Los bloques se expanden en `Ocurrencia`s al pedir un rango de días; las ocurrencias no se guardan.

Una tarea sin día es válida (bandeja de entrada). `completar`, `reabrir` y `mover` devuelven una tarea nueva: las entidades son inmutables, como en training.

Solapes: dos intervalos se solapan si comparten algún instante; tocarse (9-11 y 11-12) no cuenta. `solapes(nuevo, existentes)` devuelve avisos ordenados y nunca impide guardar (regla 7). Al editar un evento no se avisa de que se pisa consigo mismo.

**Motivo:** guardar el bloque y no sus repeticiones evita miles de filas y que cambiar el horario de una asignatura obligue a editar cada semana.
## 2026-11-14 · Persistencia y casos de uso de planning

`planning.sqlite` con tres tablas independientes (`tarea`, `evento`, `bloque`), sin cascadas entre ellas. Los repositorios están ligados al usuario y `guardar` es un upsert por `id` (`session.merge`): sirve para crear y para completar, reabrir o mover. La BD repite las reglas del dominio con CHECK (prioridad, estado coherente con `hecha_en`, `fin > inicio`, día de la semana 0-6, periodo válido) y `UNIQUE(user_id, uid_externo)` para que reimportar un `.ics` no duplique eventos.

`CasosUsoPlanning` recibe la zona horaria del usuario: un «día» va de las 00:00 a las 00:00 locales y los bloques se expanden en hora local. Crear o mover un evento avisa de los eventos y clases que pisa; crear un bloque avisa de los bloques que pisa (mismo día, horas y periodos que coinciden). Los avisos nunca impiden guardar.

`agenda(dia)` devuelve las citas (eventos y bloques, por hora), las tareas del día (pendientes primero, después por prioridad) y las atrasadas (pendientes de días anteriores). Un evento que cruza la medianoche sale en los dos días.

## 2026-11-14 · API de planning

Rutas: `GET /planning/agenda?dia=` (por defecto, hoy en la zona del usuario); tareas: `POST /planning/tasks`, `GET /planning/tasks/inbox`, `POST /planning/tasks/{id}/complete|reopen|move` y `DELETE /planning/tasks/{id}`; eventos: `POST /planning/events`, `POST /planning/events/{id}/move` y `DELETE /planning/events/{id}`; bloques: `POST/GET /planning/blocks` y `DELETE /planning/blocks/{id}`. Errores: no encontrado 404, el resto de errores de dominio 422, con `{"detail": "..."}`.

Completar, reabrir y mover son rutas con verbo en lugar de un `PATCH` genérico: cada una es un caso de uso y el agente las usará como herramientas separadas. Una hora **sin zona** («2026-11-16T09:00») se entiende en la zona del usuario y las horas salen siempre en esa zona, para que la página y el agente no tengan que tratar con UTC. Crear o mover un evento y crear un bloque devuelven `avisos` con los solapes.

## 2026-11-14 · Página «Mañana»

Muestra la agenda de mañana por defecto (con «Hoy» y «Otro» para cambiar de día): horario del día (clases y eventos), tareas con casilla para marcarlas, atrasadas con un botón para pasarlas a ese día, y formularios para añadir tarea, evento y bloque semanal. Las acciones van en callbacks de Streamlit, que llaman a la API antes de volver a pintar; los avisos de solape se guardan en `session_state` y se enseñan en la siguiente pasada. El día de «hoy» lo da `GET /planning/agenda`, así la página no calcula fechas.
