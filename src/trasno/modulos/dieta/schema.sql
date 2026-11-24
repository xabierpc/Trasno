-- dieta.db: lista semanal de lo que se puede comer y lo que no.

CREATE TABLE IF NOT EXISTS alimento (
    id          INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL,
    lunes       TEXT    NOT NULL,               -- 'YYYY-MM-DD', lunes de la semana
    nombre      TEXT    NOT NULL COLLATE NOCASE,
    permitido   INTEGER NOT NULL CHECK (permitido IN (0, 1)),   -- 1 si, 0 no
    UNIQUE (user_id, lunes, nombre)
);
CREATE INDEX IF NOT EXISTS idx_alimento_user_lunes ON alimento (user_id, lunes);
