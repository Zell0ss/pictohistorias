CREATE TABLE IF NOT EXISTS picto (
  id            INT PRIMARY KEY,
  keywords      JSON NOT NULL,
  categories    JSON,
  tags          JSON,
  descripcion   TEXT,
  schematic     BOOLEAN DEFAULT FALSE,
  cacheado      BOOLEAN DEFAULT FALSE,
  actualizado   DATETIME
);

ALTER TABLE picto
  ADD COLUMN IF NOT EXISTS sex BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS violence BOOLEAN DEFAULT FALSE;

CREATE TABLE IF NOT EXISTS diccionario (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  concepto      VARCHAR(80) NOT NULL UNIQUE,
  alias         JSON,
  tipo          ENUM('picto','foto') NOT NULL,
  picto_id      INT NULL,
  foto_path     VARCHAR(255) NULL,
  opciones      JSON,
  creado        DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS historia (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  titulo        VARCHAR(160) NOT NULL,
  prompt        TEXT NOT NULL,
  creada        DATETIME DEFAULT CURRENT_TIMESTAMP,
  actualizada   DATETIME ON UPDATE CURRENT_TIMESTAMP,
  archivada     BOOLEAN DEFAULT FALSE
);

ALTER TABLE historia
  ADD COLUMN IF NOT EXISTS creada_por VARCHAR(255) NULL;

CREATE TABLE IF NOT EXISTS paso (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  historia_id   INT NOT NULL,
  orden         TINYINT NOT NULL,
  frase         TEXT NOT NULL,
  concepto      VARCHAR(80),
  imagen_tipo   ENUM('picto','foto') NOT NULL,
  picto_id      INT NULL,
  foto_path     VARCHAR(255) NULL,
  candidatos    JSON,
  FOREIGN KEY (historia_id) REFERENCES historia(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS concepto_embedding (
  concepto      VARCHAR(160) PRIMARY KEY,
  embedding     JSON NOT NULL,
  creado        DATETIME DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE paso
  ADD COLUMN IF NOT EXISTS candidatos_concepto JSON,
  ADD COLUMN IF NOT EXISTS concepto_ganador VARCHAR(80),
  ADD COLUMN IF NOT EXISTS score_ganador FLOAT;
