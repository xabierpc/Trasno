-- pasos.db: una fila por usuario y dia.

CREATE TABLE IF NOT EXISTS pasos (
    id              INTEGER PRIMARY KEY,
    user_id         INTEGER NOT NULL,
    fecha           TEXT    NOT NULL,               -- 'YYYY-MM-DD'
    pasos           INTEGER NOT NULL CHECK (pasos >= 0),
    UNIQUE (user_id, fecha)
);
