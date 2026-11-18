-- agenda.db: tareas y eventos puntuales.

CREATE TABLE IF NOT EXISTS tarea (
    id              INTEGER PRIMARY KEY,
    user_id         INTEGER NOT NULL,
    titulo          TEXT    NOT NULL,
    descripcion     TEXT,
    fecha           TEXT,                       -- 'YYYY-MM-DD', dia planificado (opcional)
    fecha_limite    TEXT,
    prioridad       INTEGER NOT NULL DEFAULT 2 CHECK (prioridad IN (1, 2, 3)),  -- 1 alta, 3 baja
    estado          TEXT    NOT NULL DEFAULT 'pendiente'
                    CHECK (estado IN ('pendiente', 'en_curso', 'hecha', 'cancelada')),
    creada_en       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    completada_en   TEXT
);
CREATE INDEX IF NOT EXISTS idx_tarea_user_fecha ON tarea (user_id, fecha);

CREATE TABLE IF NOT EXISTS evento (
    id          INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL,
    titulo      TEXT    NOT NULL,
    descripcion TEXT,
    inicio      TEXT    NOT NULL,               -- 'YYYY-MM-DD HH:MM'
    fin         TEXT    NOT NULL,
    ubicacion   TEXT,
    CHECK (fin > inicio)
);
-- Sin restriccion de solape: se avisa desde el servicio pero se guarda.
CREATE INDEX IF NOT EXISTS idx_evento_user_inicio ON evento (user_id, inicio);

-- Dias marcados en el calendario (version 2 del esquema).
CREATE TABLE IF NOT EXISTS dia_importante (
    id          INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL,
    fecha       TEXT    NOT NULL,               -- 'YYYY-MM-DD'
    nota        TEXT,
    UNIQUE (user_id, fecha)
);
