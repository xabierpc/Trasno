-- core.db: lo unico que es del nucleo. Nunca guarda datos de un modulo.

CREATE TABLE IF NOT EXISTS usuario (
    id          INTEGER PRIMARY KEY,
    nombre      TEXT    NOT NULL,
    creado_en   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS configuracion (
    user_id     INTEGER NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    clave       TEXT    NOT NULL,
    valor       TEXT    NOT NULL,
    PRIMARY KEY (user_id, clave)
);

-- Interruptor de cada modulo. Si no hay fila, el modulo esta activo.
CREATE TABLE IF NOT EXISTS estado_modulo (
    user_id     INTEGER NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    modulo      TEXT    NOT NULL,
    activo      INTEGER NOT NULL CHECK (activo IN (0, 1)),
    PRIMARY KEY (user_id, modulo)
);
