-- peso.db: una fila por usuario y dia.

CREATE TABLE IF NOT EXISTS peso (
    id              INTEGER PRIMARY KEY,
    user_id         INTEGER NOT NULL,
    fecha           TEXT    NOT NULL,               -- 'YYYY-MM-DD'
    kg              REAL NOT NULL CHECK (kg > 0),
    UNIQUE (user_id, fecha)
);
