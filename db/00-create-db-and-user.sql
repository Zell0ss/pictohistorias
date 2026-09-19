-- Plantilla de referencia. NO contiene un password real.
-- Uso real: ver el fichero local correspondiente con el password real (patrón db/*.local.sql, gitignored).
CREATE DATABASE IF NOT EXISTS pictohistorias_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'pictohistorias'@'localhost' IDENTIFIED BY '<PASSWORD>';
GRANT ALL PRIVILEGES ON pictohistorias_db.* TO 'pictohistorias'@'localhost';
FLUSH PRIVILEGES;
