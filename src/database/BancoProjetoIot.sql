-- ============================================================================
-- Banco de Dados: sistema_iot
-- Projeto: CampusSmart - Monitoramento e Automação IoT
-- ============================================================================

CREATE DATABASE IF NOT EXISTS `sistema_iot`;
USE `sistema_iot`;

SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT;
SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS;
SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION;
SET NAMES utf8mb4;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO';

-- ----------------------------------------------------------------------------
-- Remoção segura das tabelas (ordem reversa de dependência)
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS `telemetrias`;
DROP TABLE IF EXISTS `avisos_oled`;
DROP TABLE IF EXISTS `salas`;

-- ----------------------------------------------------------------------------
-- Estrutura da tabela: salas
-- ----------------------------------------------------------------------------
CREATE TABLE `salas` (
  `id` int NOT NULL AUTO_INCREMENT,
  `nome` varchar(100) NOT NULL,
  `modo_operacao` enum('AUTO','ON','OFF') DEFAULT 'AUTO',
  `status_ocupado` tinyint(1) DEFAULT '0',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------------------------------------------------------
-- Estrutura da tabela: avisos_oled
-- ----------------------------------------------------------------------------
CREATE TABLE `avisos_oled` (
  `id` int NOT NULL AUTO_INCREMENT,
  `sala_id` int NOT NULL,
  `mensagem` varchar(255) NOT NULL,
  `timestamp` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_avisos_sala_id` (`sala_id`),
  CONSTRAINT `avisos_oled_ibfk_1` FOREIGN KEY (`sala_id`) REFERENCES `salas` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------------------------------------------------------
-- Estrutura da tabela: telemetrias
-- ----------------------------------------------------------------------------
CREATE TABLE `telemetrias` (
  `id` int NOT NULL AUTO_INCREMENT,
  `sala_id` int NOT NULL,
  `ocupado` tinyint(1) NOT NULL,
  `potencia_w` float NOT NULL,
  `corrente_ma` int NOT NULL,
  `timestamp` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_telemetrias_sala_id` (`sala_id`),
  CONSTRAINT `telemetrias_ibfk_1` FOREIGN KEY (`sala_id`) REFERENCES `salas` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------------------------------------------------------
-- Carga Inicial (Seeds) para Salas Monitoradas
-- ----------------------------------------------------------------------------
INSERT INTO `salas` (`id`, `nome`, `modo_operacao`, `status_ocupado`) VALUES
  (101, 'Sala 101', 'AUTO', 1),
  (102, 'Sala 102', 'AUTO', 0),
  (103, 'Sala 103', 'AUTO', 1),
  (104, 'Lab. Informática', 'AUTO', 0),
  (105, 'Auditório', 'AUTO', 0),
  (201, 'Sala 201', 'AUTO', 1),
  (202, 'Sala 202', 'AUTO', 0),
  (203, 'Biblioteca', 'AUTO', 1)
ON DUPLICATE KEY UPDATE `nome` = VALUES(`nome`), `modo_operacao` = VALUES(`modo_operacao`);

SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
SET SQL_MODE=@OLD_SQL_MODE;
SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT;
SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS;
SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION;
