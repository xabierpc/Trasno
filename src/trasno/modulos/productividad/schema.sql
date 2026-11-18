-- productividad.db: horas productivas con el cronometro integrado.

CREATE TABLE IF NOT EXISTS categoria (
    id          INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL,
    nombre      TEXT    NOT NULL,
    color       TEXT,
    archivada   INTEGER NOT NULL DEFAULT 0 CHECK (archivada IN (0, 1)),
    UNIQUE (user_id, nombre)
);

-- Pausar = cerrar la sesion y abrir otra.
CREATE TABLE IF NOT EXISTS sesion_productiva (
    id              INTEGER PRIMARY KEY,
    user_id         INTEGER NOT NULL,
    categoria_id    INTEGER NOT NULL REFERENCES categoria(id) ON DELETE RESTRICT,
    tarea_id        INTEGER,                    -- id en agenda.db, solo si el modulo agenda esta activo
    fecha           TEXT    NOT NULL,
    inicio          TEXT    NOT NULL,
    fin             TEXT,                       -- NULL = cronometro en marcha
    notas           TEXT,
    CHECK (fin IS NULL OR fin > inicio)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_cronometro_activo ON sesion_productiva (user_id) WHERE fin IS NULL;
CREATE INDEX IF NOT EXISTS idx_sesion_prod_user_fecha ON sesion_productiva (user_id, fecha);
