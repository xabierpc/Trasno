# Decisiones

Registro de decisiones de diseño. Una entrada por decisión: fecha, decisión y motivo.

## 2026-11-14 · Ventana de madrugada: 00:00-06:00

Los registros con timestamp entre las 00:00 y las 06:00 (hora de `Europe/Madrid`) son ambiguos: se pregunta al usuario a qué día lógico cuentan. Es configurable en `Settings.ventana_madrugada`.

**Motivo:** acostarse tarde no debe hacer que un entreno o una métrica caiga en el día siguiente sin querer.

## 2026-11-14 · Log del agente en `core.sqlite`

Cada herramienta que usa el agente se registra en una tabla de `core.sqlite`, no en una base de datos propia del agente.

**Motivo:** el log es transversal (registra acciones sobre cualquier módulo) y lo consulta el core; así hay un único sitio para auditar lo que hizo el agente.
