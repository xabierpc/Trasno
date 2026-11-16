-- entreno.db: catalogo de ejercicios, rutina semanal (plan) y registro real.

CREATE TABLE IF NOT EXISTS ejercicio (
    id              INTEGER PRIMARY KEY,
    user_id         INTEGER NOT NULL,
    nombre          TEXT    NOT NULL,
    tipo            TEXT    NOT NULL CHECK (tipo IN ('fuerza', 'cardio')),
    grupo_muscular  TEXT,
    UNIQUE (user_id, nombre)
);

-- ---------- PLAN ----------
CREATE TABLE IF NOT EXISTS rutina (
    id          INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL,
    nombre      TEXT    NOT NULL,
    activa      INTEGER NOT NULL DEFAULT 0 CHECK (activa IN (0, 1)),
    UNIQUE (user_id, nombre)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_rutina_activa ON rutina (user_id) WHERE activa = 1;

CREATE TABLE IF NOT EXISTS rutina_dia (
    id          INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL,
    rutina_id   INTEGER NOT NULL REFERENCES rutina(id) ON DELETE CASCADE,
    dia_semana  INTEGER NOT NULL CHECK (dia_semana BETWEEN 0 AND 6),
    nombre      TEXT    NOT NULL,
    UNIQUE (rutina_id, dia_semana)
);

CREATE TABLE IF NOT EXISTS rutina_ejercicio (
    id                   INTEGER PRIMARY KEY,
    user_id              INTEGER NOT NULL,
    rutina_dia_id        INTEGER NOT NULL REFERENCES rutina_dia(id) ON DELETE CASCADE,
    ejercicio_id         INTEGER NOT NULL REFERENCES ejercicio(id) ON DELETE RESTRICT,
    orden                INTEGER NOT NULL,
    series_objetivo      INTEGER,
    reps_objetivo        INTEGER,
    peso_objetivo_kg     REAL,
    duracion_objetivo_s  INTEGER,
    distancia_objetivo_m REAL,
    UNIQUE (rutina_dia_id, orden)
);

-- ---------- REGISTRO ----------
CREATE TABLE IF NOT EXISTS sesion (
    id              INTEGER PRIMARY KEY,
    user_id         INTEGER NOT NULL,
    fecha           TEXT    NOT NULL,           -- dia al que cuenta (regla de madrugada)
    rutina_dia_id   INTEGER REFERENCES rutina_dia(id) ON DELETE SET NULL,
    inicio          TEXT,
    fin             TEXT,
    notas           TEXT,
    CHECK (fin IS NULL OR inicio IS NULL OR fin > inicio)
);
CREATE INDEX IF NOT EXISTS idx_sesion_user_fecha ON sesion (user_id, fecha);

CREATE TABLE IF NOT EXISTS serie_fuerza (
    id              INTEGER PRIMARY KEY,
    user_id         INTEGER NOT NULL,
    sesion_id       INTEGER NOT NULL REFERENCES sesion(id) ON DELETE CASCADE,
    ejercicio_id    INTEGER NOT NULL REFERENCES ejercicio(id) ON DELETE RESTRICT,
    orden           INTEGER NOT NULL,
    reps            INTEGER NOT NULL CHECK (reps >= 0),
    peso_kg         REAL    NOT NULL DEFAULT 0 CHECK (peso_kg >= 0),
    rpe             REAL    CHECK (rpe IS NULL OR rpe BETWEEN 1 AND 10),
    UNIQUE (sesion_id, ejercicio_id, orden)
);

CREATE TABLE IF NOT EXISTS registro_cardio (
    id              INTEGER PRIMARY KEY,
    user_id         INTEGER NOT NULL,
    sesion_id       INTEGER NOT NULL REFERENCES sesion(id) ON DELETE CASCADE,
    ejercicio_id    INTEGER NOT NULL REFERENCES ejercicio(id) ON DELETE RESTRICT,
    duracion_s      INTEGER NOT NULL CHECK (duracion_s > 0),
    distancia_m     REAL    CHECK (distancia_m IS NULL OR distancia_m >= 0),
    notas           TEXT
);
