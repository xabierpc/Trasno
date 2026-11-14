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
