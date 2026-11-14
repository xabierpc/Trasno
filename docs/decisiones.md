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
