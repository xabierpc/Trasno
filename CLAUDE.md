# Trasno

Asistente personal en Python (un "Jarvis") que guarda los datos de la vida diaria —tareas, horario, entrenos, peso, hábitos, estadísticas— y hace de asistente: avisos, briefing diario y agente con herramientas. Lo desarrollan dos personas, Xabi y Raúl, en paralelo.

Documentos de referencia en `docs/`: `jarvis-plan.md` (plan y hoja de ruta), `arquitectura-datos.md`, `core-como-enchufar-un-modulo.md`. Léelos antes de diseñar algo nuevo.

## Stack

uv · Python 3.12 · SQLite + SQLAlchemy 2.0 · Alembic · FastAPI + uvicorn · httpx · Streamlit (multipágina) · pandas · Plotly · pydantic-settings · APScheduler · keyring · pytest · ruff

## Comandos

```bash
uv sync                                   # instalar
uv run ruff check . && uv run ruff format --check .
uv run pytest                             # todos los tests
uv run trasno migrate                     # aplica las migraciones de core y de cada módulo
uv run trasno backup                      # copia de seguridad de todos los .sqlite
uv run python main.py                     # API en 127.0.0.1:8000
uv run streamlit run interfaces/dashboard/app.py
```

Antes de dar una tarea por hecha: `ruff check`, `ruff format --check` y `pytest` en verde.

## Estructura

```
core/                 config, db (make_engine), bus de eventos, loader de módulos, scheduler, backup, contracts.py
modules/<modulo>/
  __init__.py         register(ctx: AppContext)  ← único punto de enchufe
  domain/             Python puro: entidades, reglas, errores
  application/        casos de uso + ports.py (interfaces de repositorios)
  infrastructure/     modelos SQLAlchemy, repositorios SQL, migrations/ (Alembic propio)
agent/                registro de herramientas, adaptador LLM, log de acciones
interfaces/api/       app factory de FastAPI
interfaces/dashboard/ app.py (shell) + pages/
tests/<modulo>/
main.py
```

## Reglas de arquitectura (no negociables)

1. **Capas.** `domain` no importa SQLAlchemy, FastAPI, Streamlit ni nada de infraestructura. Las dependencias apuntan hacia dentro.
2. **Un módulo nunca importa a otro.** Se comunican publicando eventos en el `EventBus` o mediante ports. `analytics` lee series vía `SeriesProvider`, nunca importando módulos.
3. **Un SQLite por módulo** en `data/<modulo>.sqlite`, creado con `make_engine(modulo)`. Cada módulo tiene su carpeta de Alembic. `PRAGMA foreign_keys=ON` y WAL siempre.
4. **Todas las tablas llevan `user_id`** (hay un solo usuario, pero se prepara para varios). Borrado real, sin soft delete.
5. **Fechas:** se guarda el timestamp con zona horaria y la `logical_date` por separado. Dentro de la ventana de madrugada (por defecto 00:00-06:00) se pregunta al usuario a qué día cuenta.
6. **Métricas:** si se repite una métrica el mismo día, sobrescribe (`on_duplicate=replace`) salvo que esté configurada como `keep_all`.
7. **Solapes de horario:** avisan pero dejan guardar.
8. **Los módulos se descubren solos.** Un módulo nuevo no obliga a tocar código del core ni ninguna lista central.
9. **Streamlit es un cliente fino:** las páginas leen inputs, llaman a la API con el cliente httpx (creado con `st.cache_resource`) y pintan. Nada de lógica de negocio ni acceso a BD en las páginas.
10. **Seguridad:** la API escucha solo en `127.0.0.1`. Secretos (tokens OAuth, claves de API) en `keyring`, nunca en el código ni en un `.env` versionado. El agente pide confirmación antes de cualquier acción con efectos externos y registra cada herramienta que usa en el log de `core.sqlite`.
11. **Cada caso de uso es candidato a herramienta del agente:** firmas claras, tipos explícitos y docstring de una línea.

## Estilo

- Tipado en todo (`from __future__ import annotations`), dataclasses o Pydantic para datos.
- Nombres de dominio en español (`registrar_metrica`, `MetricEntry` se acepta), comentarios y docstrings en español.
- Funciones pequeñas; nada de lógica en `__init__.py` salvo `register(ctx)`.
- Errores de dominio como excepciones propias, no `ValueError` genéricos.

## Tests

- TDD: primero el test, luego el código mínimo.
- Dominio y casos de uso: tests unitarios con repositorios en memoria.
- Infraestructura: SQLite en memoria o `tmp_path`, nunca `data/` real.
- API: `TestClient` montando solo el router del módulo.

## Propiedad del código

Cada carpeta tiene un dueño y solo él la edita. Si una tarea necesita tocar una carpeta ajena, **para y avísame**: se pide al dueño o se abre un issue.

| Xabi | Raúl |
|---|---|
| `core/`, `modules/analytics/`, `modules/planning/`, `interfaces/api/`, `interfaces/dashboard/app.py`, `main.py`, scheduler, briefing | `modules/tracking/`, `modules/training/`, `agent/`, sus páginas en `interfaces/dashboard/pages/` |

Cambiar `core/contracts.py` requiere un PR propio aprobado por el otro antes de usarlo.

## Git

- Ramas: `main` ← `dev` ← `feature/<ID>-<nombre>` (p. ej. `feature/X5-bus`).
- PR pequeño a `dev`, revisado por el otro. Nunca push directo a `dev` ni a `main`.
- Commits en español, en imperativo: `Añade bus de eventos con aislamiento de errores`.
- Nueva dependencia: PR aparte con `uv add`. Conflicto en `uv.lock`: se regenera con `uv lock`, nunca a mano.

## Cómo trabajar conmigo

- Una tarea cada vez. Antes de crear ficheros, dime cuáles y por qué.
- Explica brevemente cada decisión de diseño: queremos entender el código, no solo tenerlo.
- Si algo del plan no está decidido, pregunta en lugar de suponer.
