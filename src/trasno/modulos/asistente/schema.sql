-- asistente.db: correo y recordatorios.

-- Las credenciales NO van aqui: van al llavero del sistema (keyring).
CREATE TABLE IF NOT EXISTS cuenta_correo (
    id          INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL,
    proveedor   TEXT    NOT NULL CHECK (proveedor IN ('gmail', 'imap')),
    direccion   TEXT    NOT NULL,
    activa      INTEGER NOT NULL DEFAULT 1 CHECK (activa IN (0, 1)),
    UNIQUE (user_id, direccion)
);

CREATE TABLE IF NOT EXISTS correo (
    id          INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL,
    cuenta_id   INTEGER NOT NULL REFERENCES cuenta_correo(id) ON DELETE CASCADE,
    message_id  TEXT    NOT NULL,
    remitente   TEXT,
    asunto      TEXT,
    recibido_en TEXT    NOT NULL,
    leido       INTEGER NOT NULL DEFAULT 0 CHECK (leido IN (0, 1)),
    resumen     TEXT,
    UNIQUE (cuenta_id, message_id)
);
CREATE INDEX IF NOT EXISTS idx_correo_user_fecha ON correo (user_id, recibido_en);

CREATE TABLE IF NOT EXISTS recordatorio (
    id              INTEGER PRIMARY KEY,
    user_id         INTEGER NOT NULL,
    texto           TEXT    NOT NULL,
    momento         TEXT    NOT NULL,
    repeticion      TEXT    NOT NULL DEFAULT 'ninguna'
                    CHECK (repeticion IN ('ninguna', 'diaria', 'semanal', 'mensual')),
    origen_tipo     TEXT    CHECK (origen_tipo IS NULL OR origen_tipo IN ('tarea', 'evento')),
    origen_id       INTEGER,                    -- id en agenda.db, solo si agenda esta activo
    completado      INTEGER NOT NULL DEFAULT 0 CHECK (completado IN (0, 1)),
    creado_en       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    CHECK ((origen_tipo IS NULL AND origen_id IS NULL) OR (origen_tipo IS NOT NULL AND origen_id IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS idx_recordatorio_pendiente ON recordatorio (user_id, completado, momento);
