-- nutricion.db: una fila por usuario y dia.

CREATE TABLE IF NOT EXISTS nutricion (
    id              INTEGER PRIMARY KEY,
    user_id         INTEGER NOT NULL,
    fecha           TEXT    NOT NULL,               -- 'YYYY-MM-DD'
    kcal            REAL NOT NULL CHECK (kcal >= 0),
    proteina_g      REAL NOT NULL CHECK (proteina_g >= 0),
    carbohidratos_g REAL NOT NULL CHECK (carbohidratos_g >= 0),
    grasas_g        REAL NOT NULL CHECK (grasas_g >= 0),
    UNIQUE (user_id, fecha)
);
