-- sueno.db: una fila por usuario y dia.
-- fecha = dia en el que te despiertas.

CREATE TABLE IF NOT EXISTS sueno (
    id              INTEGER PRIMARY KEY,
    user_id         INTEGER NOT NULL,
    fecha           TEXT    NOT NULL,               -- 'YYYY-MM-DD'
    horas           REAL NOT NULL CHECK (horas >= 0 AND horas <= 24),
    calidad         INTEGER NOT NULL CHECK (calidad BETWEEN 1 AND 5),
    UNIQUE (user_id, fecha)
);
