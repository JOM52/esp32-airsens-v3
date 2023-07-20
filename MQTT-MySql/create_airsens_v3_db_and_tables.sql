-- Batch pour la création de la base de donnee airsens
-- 03.07.2023 Joseph Metrailler
-- --------------------------------------------------------------
-- si elle existe, supprimer la db mqtt existante et la recreer
DROP DATABASE IF EXISTS airsens;
CREATE DATABASE airsens;
USE airsens;
-- if exists drop tables (remove comment if needed)
DROP TABLE IF EXISTS airsens;
DROP TABLE IF EXISTS sensor_id;
DROP TABLE IF EXISTS sensor_location;
DROP TABLE IF EXISTS sensor_type;
-- --------------------------------------------------------------
CREATE TABLE airsens
(
  id INT NOT NULL AUTO_INCREMENT,
  time_stamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  sensor_id INT NOT NULL,
  sensor_location INT NOT NULL,
  sensor_type INT NOT NULL,
  quantity int NOT NULL,
  value DOUBLE NOT NULL,
  PRIMARY KEY (id),
  INDEX i_date (time_stamp),
  INDEX i_id (id),
  UNIQUE(id)
);
CREATE TABLE sensor_id
(
  id INT NOT NULL AUTO_INCREMENT,
  sensor_id VARCHAR(20) NOT NULL,
  PRIMARY KEY (id),
  INDEX i_id (id),
  UNIQUE(id)
);
CREATE TABLE sensor_location
(
  id INT NOT NULL AUTO_INCREMENT,
  sensor_location VARCHAR(20) NOT NULL,
  PRIMARY KEY (id),
  INDEX i_id (id),
  UNIQUE(id)
);
CREATE TABLE sensor_type
(
  id INT NOT NULL AUTO_INCREMENT,
  sensor_type VARCHAR(20) NOT NULL,
  PRIMARY KEY (id),
  INDEX i_id (id),
  UNIQUE(id)
);
CREATE TABLE quantity
(
  id INT NOT NULL AUTO_INCREMENT,
  quantity VARCHAR(20) NOT NULL,
  PRIMARY KEY (id),
  INDEX i_id (id),
  UNIQUE(id)
);
