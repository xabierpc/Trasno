# Trasno

Asistente personal modular en Python (un «Jarvis»): registra tareas, horario, entrenos, peso y hábitos en SQLite, prepara un briefing diario y tiene un agente con LLM que usa todo eso como herramientas. API FastAPI, panel Streamlit, arquitectura por capas y módulos enchufables.

## Qué hace (v0.5)

| Módulo | Qué guarda o hace |
|---|---|
| `tracking` | Métricas configurables (peso, pasos, sueño, ánimo, hábitos…), rachas y cumplimiento |
| `training` | Sesiones → ejercicios → series, 1RM estimado, volumen y récords |
| `planning` | Tareas, eventos, clases semanales, solapes, agenda del día e importación de `.ics` |
| `briefing` | Resumen del día a una hora fija, con notificación de escritorio |
| `agent` | Chat con un LLM que registra, consulta y propone cambios (con confirmación) |

Páginas del panel: **Peso**, **Registro diario**, **Entrenos**, **Mañana** (agenda), **Briefing** y **Trasno** (chat).

## Puesta en marcha

Requisitos: [uv](https://docs.astral.sh/uv/) y Python 3.12.

```bash
uv sync                    # instala dependencias
uv run trasno migrate      # crea o actualiza las bases de datos en data/
uv run python main.py      # API en http://127.0.0.1:8000 (documentación en /docs)
uv run streamlit run interfaces/dashboard/app.py   # panel en http://localhost:8501
```

La API y el panel van en terminales distintas. Los trabajos programados (el briefing) solo se ejecutan mientras la API está en marcha.

## Configuración

Se copia `.env.example` a `.env` y se descomenta lo que haga falta. Los secretos nunca van en `.env`: van en el llavero del sistema.

**LLM del agente** (cualquier API compatible con OpenAI):

- Ollama en local (por defecto): instalar Ollama y `ollama pull qwen3:8b`.
- Groq u otro servicio: en `.env`, `TRASNO_LLM_URL` y `TRASNO_LLM_MODELO`, y la clave con `uv run keyring set trasno llm`.

Otros ajustes: `TRASNO_BRIEFING_HORA` (07:30), `TRASNO_TIMEZONE` (Europe/Madrid), `TRASNO_DATA_DIR`, `TRASNO_BACKUP_DIR`.

## Comandos

```bash
uv run pytest                                   # tests
uv run ruff check . && uv run ruff format --check .
uv run trasno backup                            # copia de seguridad de los .sqlite
```

## Documentación

- `CLAUDE.md`: reglas de arquitectura, estilo y forma de trabajar.
- `docs/decisiones.md`: cada decisión de diseño con su motivo.
