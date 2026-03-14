-- Esquema de capacitacion (opcion A estados, evaluador unico)
-- Ejecutar con psql tras exportar tus variables de conexion
-- Ejemplo: psql "host=$DB_HOST port=${DB_PORT:-5432} dbname=$DB_NAME user=$DB_USER password=$DB_PASSWORD" -f docs/capacitacion_schema.sql

DO $$ BEGIN
  CREATE TYPE training_estado AS ENUM ('planned','in_progress','paused','finished','cancelled');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS capacitacion_curso (
  id SERIAL PRIMARY KEY,
  nombre VARCHAR(100) NOT NULL UNIQUE,
  descripcion TEXT,
  activo BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS capacitacion_tema (
  id SERIAL PRIMARY KEY,
  curso_id INT NOT NULL REFERENCES capacitacion_curso(id) ON DELETE CASCADE,
  nombre VARCHAR(150) NOT NULL,
  orden SMALLINT NOT NULL,
  descripcion TEXT,
  duracion_ref INTERVAL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  UNIQUE (curso_id, nombre),
  UNIQUE (curso_id, orden)
);

CREATE TABLE IF NOT EXISTS capacitacion_evaluador (
  id SERIAL PRIMARY KEY,
  practicante_id INT NOT NULL UNIQUE REFERENCES practicante(id) ON DELETE CASCADE,
  activo BOOLEAN NOT NULL DEFAULT TRUE,
  notas TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS capacitacion_progreso (
  id SERIAL PRIMARY KEY,
  practicante_id INT NOT NULL REFERENCES practicante(id) ON DELETE CASCADE,
  curso_id INT NOT NULL REFERENCES capacitacion_curso(id) ON DELETE CASCADE,
  tema_id INT NOT NULL REFERENCES capacitacion_tema(id) ON DELETE CASCADE,
  evaluador_practicante_id INT NULL REFERENCES capacitacion_evaluador(practicante_id) ON DELETE SET NULL,
  estado training_estado NOT NULL DEFAULT 'planned',
  fecha_inicio TIMESTAMP NULL,
  fecha_fin TIMESTAMP NULL,
  acumulado INTERVAL NOT NULL DEFAULT INTERVAL '0 seconds',
  ultima_reanudacion TIMESTAMP NULL,
  duracion_final INTERVAL NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
  UNIQUE (practicante_id, tema_id),
  CHECK (fecha_fin IS NULL OR fecha_inicio IS NULL OR fecha_fin >= fecha_inicio)
);

CREATE INDEX IF NOT EXISTS idx_prog_estado ON capacitacion_progreso (estado);
CREATE INDEX IF NOT EXISTS idx_prog_eval ON capacitacion_progreso (evaluador_practicante_id);

