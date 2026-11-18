-- horario.db: horario recurrente de clase / trabajo.

CREATE TABLE IF NOT EXISTS bloque_horario (
    id              INTEGER PRIMARY KEY,
    user_id         INTEGER NOT NULL,
    tipo            TEXT    NOT NULL CHECK (tipo IN ('clase', 'trabajo', 'otro')),
    titulo          TEXT    NOT NULL,
    dia_semana      INTEGER NOT NULL CHECK (dia_semana BETWEEN 0 AND 6),  -- 0 lunes
    hora_inicio     TEXT    NOT NULL,           -- 'HH:MM'
    hora_fin        TEXT    NOT NULL,
    ubicacion       TEXT,
    vigente_desde   TEXT    NOT NULL,
    vigente_hasta   TEXT,
    CHECK (hora_fin > hora_inicio),
    CHECK (vigente_hasta IS NULL OR vigente_hasta >= vigente_desde)
);
CREATE INDEX IF NOT EXISTS idx_bloque_user_dia ON bloque_horario (user_id, dia_semana);

CREATE TABLE IF NOT EXISTS excepcion_horario (
    id              INTEGER PRIMARY KEY,
    user_id         INTEGER NOT NULL,
    bloque_id       INTEGER NOT NULL REFERENCES bloque_horario(id) ON DELETE CASCADE,
    fecha           TEXT    NOT NULL,
    tipo            TEXT    NOT NULL CHECK (tipo IN ('cancelado', 'modificado')),
    hora_inicio     TEXT,
    hora_fin        TEXT,
    motivo          TEXT,
    UNIQUE (bloque_id, fecha),
    CHECK (tipo = 'cancelado' OR (hora_inicio IS NOT NULL AND hora_fin IS NOT NULL AND hora_fin > hora_inicio))
);
