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
