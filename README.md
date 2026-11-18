# Trasno

Jarvis personal con Streamlit. Arquitectura de **plugins (microkernel)**: un núcleo pequeño y módulos que se pueden añadir, desactivar o borrar.

## Arrancar

```bash
uv sync            # o: pip install "streamlit>=1.50" pandas
uv run streamlit run app.py
```

Las bases de datos se crean solas en `data/` (una por módulo + `core.db`).

## Estructura

```
app.py              punto de entrada
nucleo/             siempre presente
  jarvis.py         carga módulos, configuración, coordina
  interfaz.py       marco Streamlit: una página (st.navigation) por módulo activo,
                    portada, ajustes, pregunta de madrugada
  avisos.py         mensajes que sobreviven a st.rerun()
  fechas.py         regla de madrugada y utilidades de fechas
  registro.py       descubre los módulos de modulos/
  contrato.py       clase Modulo que cumple todo plugin
  db.py, core.sql   core.db: usuario, configuración, módulos activos
  metricas.py       utilidad común para métricas diarias
modulos/<nombre>/   un plugin
  modulo.py         ficha para el núcleo (crear(carpeta) -> Modulo)
  pagina.py         pantalla Streamlit       (presentación) -> URL /<nombre>
  servicio.py       reglas de negocio        (dominio)
  repositorio.py    SQL                      (datos)
  schema.sql        tablas de <nombre>.db
```

## Reglas

1. El núcleo nunca importa un módulo concreto: los descubre.
2. Un módulo nunca importa otro. Si necesita uno, `jarvis.obtener("agenda")`, que devuelve `None` si no está.
3. Cada módulo solo toca su propia `.db`. Todas las tablas llevan `user_id`.
4. Dentro de un módulo: página → servicio → repositorio. Nunca al revés.

## Quitar un módulo

- Desde la app: **Ajustes → Módulos** (se desactiva, los datos se conservan).
- Del todo: borrar `modulos/<nombre>/` (y si quieres `data/<nombre>.db`).

## Añadir un módulo

Copiar la carpeta de uno existente (p. ej. `modulos/peso/`), cambiar nombre, tabla y campos. El núcleo lo detecta al arrancar.
