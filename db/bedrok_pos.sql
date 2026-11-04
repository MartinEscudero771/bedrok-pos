-- =====================================================================
-- Bedrok POS - Base de datos completa (MariaDB 13 / MySQL compatible)
-- Proyecto: Tienda_bedrok (Reto Factus - API Wars 2026)
-- Ruta en el proyecto: db/bedrok_pos.sql
--
-- Contenido:
--   1) Esquema completo (7 tablas: clientes, productos, facturas,
--      detalle_factura, respuestas_factus, recaudos_pay, webhook_logs)
--   2) Datos de demostracion (1 cliente + 32 productos con precios reales de demo)
--
-- Restore:
--   mysql -u root -p < db/bedrok_pos.sql
-- o dentro de mysql>  SOURCE db/bedrok_pos.sql;  (ejecutar posicionado en la carpeta db/)
--
-- NOTA: este dump NO contiene credenciales ni QR base64 de ventas reales.
--        Las credenciales de Factus viven solo en .env (no versionado).
-- =====================================================================

/*M!999999\- enable the sandbox mode */ 

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*M!100616 SET @OLD_NOTE_VERBOSITY=@@NOTE_VERBOSITY, NOTE_VERBOSITY=0 */;

/*!40000 DROP DATABASE IF EXISTS `tienda_bedrok`*/;

CREATE DATABASE /*!32312 IF NOT EXISTS*/ `tienda_bedrok` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_uca1400_ai_ci */;

USE `tienda_bedrok`;
DROP TABLE IF EXISTS `clientes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `clientes` (
  `id_cliente` int(11) NOT NULL AUTO_INCREMENT,
  `tipo_documento` varchar(10) NOT NULL,
  `numero_documento` varchar(30) NOT NULL,
  `nombres` varchar(200) NOT NULL,
  `direccion` varchar(250) DEFAULT '',
  `telefono` varchar(30) DEFAULT '',
  `correo` varchar(150) DEFAULT '',
  `codigo_organizacion` varchar(5) DEFAULT '2',
  `codigo_tributo` varchar(5) DEFAULT 'ZZ',
  `codigo_pais` varchar(5) DEFAULT 'CO',
  `codigo_municipio` varchar(10) DEFAULT '23001',
  `activo` tinyint(1) DEFAULT 1,
  `creado_en` timestamp NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id_cliente`),
  UNIQUE KEY `numero_documento` (`numero_documento`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `detalle_factura`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `detalle_factura` (
  `id_detalle` int(11) NOT NULL AUTO_INCREMENT,
  `id_factura` int(11) NOT NULL,
  `id_producto` int(11) NOT NULL,
  `cantidad` int(11) NOT NULL,
  `precio_unitario` decimal(14,2) NOT NULL,
  `porcentaje_iva` decimal(5,2) NOT NULL,
  `valor_iva` decimal(14,2) NOT NULL,
  `subtotal` decimal(14,2) NOT NULL,
  `total` decimal(14,2) NOT NULL,
  PRIMARY KEY (`id_detalle`),
  KEY `id_factura` (`id_factura`),
  KEY `id_producto` (`id_producto`),
  CONSTRAINT `1` FOREIGN KEY (`id_factura`) REFERENCES `facturas` (`id_factura`) ON DELETE CASCADE,
  CONSTRAINT `2` FOREIGN KEY (`id_producto`) REFERENCES `productos` (`id_producto`)
) ENGINE=InnoDB AUTO_INCREMENT=60 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `facturas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `facturas` (
  `id_factura` int(11) NOT NULL AUTO_INCREMENT,
  `id_cliente` int(11) NOT NULL,
  `codigo_referencia` varchar(100) NOT NULL,
  `fecha_emision` datetime DEFAULT current_timestamp(),
  `subtotal` decimal(14,2) NOT NULL DEFAULT 0.00,
  `total_iva` decimal(14,2) NOT NULL DEFAULT 0.00,
  `total` decimal(14,2) NOT NULL DEFAULT 0.00,
  `estado` varchar(20) DEFAULT 'PENDIENTE',
  `ambiente` varchar(20) DEFAULT 'SANDBOX',
  `cufe` varchar(250) DEFAULT NULL,
  `numero_factura` varchar(50) DEFAULT NULL,
  `url_pdf` text DEFAULT NULL,
  `metodo_pago` varchar(20) DEFAULT 'EFECTIVO',
  `pay_reference` varchar(100) DEFAULT NULL,
  `pay_status` varchar(20) DEFAULT 'SIN_QR',
  `moneda` varchar(5) DEFAULT NULL,
  `tasa_cambio` decimal(13,4) DEFAULT NULL,
  `monto_moneda` decimal(14,2) DEFAULT NULL,
  `cambio_moneda` decimal(14,2) DEFAULT NULL,
  `fecha_credito` date DEFAULT NULL,
  PRIMARY KEY (`id_factura`),
  UNIQUE KEY `codigo_referencia` (`codigo_referencia`),
  KEY `id_cliente` (`id_cliente`),
  CONSTRAINT `1` FOREIGN KEY (`id_cliente`) REFERENCES `clientes` (`id_cliente`)
) ENGINE=InnoDB AUTO_INCREMENT=48 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `productos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `productos` (
  `id_producto` int(11) NOT NULL AUTO_INCREMENT,
  `codigo_referencia` varchar(50) NOT NULL,
  `nombre` varchar(150) NOT NULL,
  `descripcion` varchar(250) DEFAULT '',
  `precio` decimal(14,2) NOT NULL,
  `porcentaje_iva` decimal(5,2) NOT NULL DEFAULT 19.00,
  `codigo_unidad` varchar(10) DEFAULT '94',
  `codigo_estandar` varchar(10) DEFAULT '999',
  `stock` int(11) NOT NULL DEFAULT 0,
  `activo` tinyint(1) DEFAULT 1,
  `creado_en` timestamp NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id_producto`),
  UNIQUE KEY `codigo_referencia` (`codigo_referencia`)
) ENGINE=InnoDB AUTO_INCREMENT=36 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `recaudos_pay`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `recaudos_pay` (
  `id_recaudo` int(11) NOT NULL AUTO_INCREMENT,
  `id_factura` int(11) DEFAULT NULL,
  `reference_code` varchar(100) NOT NULL,
  `amount` decimal(14,2) NOT NULL,
  `status` varchar(20) DEFAULT 'ready',
  `breb_key` varchar(100) DEFAULT NULL,
  `qr` longtext DEFAULT NULL,
  `qr_expires_at` varchar(50) DEFAULT NULL,
  `collected_at` varchar(50) DEFAULT NULL,
  `payer_json` text DEFAULT NULL,
  `raw_json` mediumtext DEFAULT NULL,
  `creado_en` timestamp NULL DEFAULT current_timestamp(),
  `actualizado_en` timestamp NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id_recaudo`),
  UNIQUE KEY `reference_code` (`reference_code`),
  KEY `id_factura` (`id_factura`),
  CONSTRAINT `1` FOREIGN KEY (`id_factura`) REFERENCES `facturas` (`id_factura`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=36 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `respuestas_factus`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `respuestas_factus` (
  `id_respuesta` int(11) NOT NULL AUTO_INCREMENT,
  `id_factura` int(11) DEFAULT NULL,
  `codigo_referencia` varchar(100) DEFAULT NULL,
  `codigo_http` int(11) DEFAULT NULL,
  `estado_api` varchar(20) DEFAULT NULL,
  `mensaje` text DEFAULT NULL,
  `solicitud_json` mediumtext DEFAULT NULL,
  `respuesta_json` mediumtext DEFAULT NULL,
  `creado_en` timestamp NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id_respuesta`),
  KEY `id_factura` (`id_factura`),
  CONSTRAINT `1` FOREIGN KEY (`id_factura`) REFERENCES `facturas` (`id_factura`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=63 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `webhook_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `webhook_logs` (
  `id_log` int(11) NOT NULL AUTO_INCREMENT,
  `reference_code` varchar(100) DEFAULT NULL,
  `payload` mediumtext DEFAULT NULL,
  `resultado` varchar(250) DEFAULT NULL,
  `creado_en` timestamp NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id_log`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*M!100616 SET NOTE_VERBOSITY=@OLD_NOTE_VERBOSITY */;


-- -------------------------------------------------------------------
-- 2) DATOS DE CATALOGO / CLIENTES
-- -------------------------------------------------------------------

/*M!999999\- enable the sandbox mode */ 

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*M!100616 SET @OLD_NOTE_VERBOSITY=@@NOTE_VERBOSITY, NOTE_VERBOSITY=0 */;

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `clientes` WRITE;
/*!40000 ALTER TABLE `clientes` DISABLE KEYS */;
INSERT INTO `clientes` VALUES
(1,'13','1234567890','Consumidor Final','Calle 10 5-20','3001234567','cliente@test.com','2','ZZ','CO','23001',1,'2026-11-04 16:47:29'),
(6,'13','1137995222','tu mae','','','','2','ZZ','CO','23001',1,'2026-11-04 18:58:31');
/*!40000 ALTER TABLE `clientes` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `productos` WRITE;
/*!40000 ALTER TABLE `productos` DISABLE KEYS */;
INSERT INTO `productos` VALUES
(1,'BED-001','Cafe molido 500g','Cafe premium',12500.00,19.00,'94','999',32,1,'2026-11-04 16:47:29'),
(2,'BED-002','Arroz 1kg','Arroz blanco',5200.00,19.00,'94','999',18,1,'2026-11-04 16:47:29'),
(3,'BED-003','Panela 1kg','Panela natural',6800.00,19.00,'94','999',76,1,'2026-11-04 16:47:29'),
(7,'BED-004','Leche entera 1L','Leche larga vida',4500.00,0.00,'94','999',120,1,'2026-11-04 17:37:16'),
(8,'BED-005','Huevo AA cubeta x30','Huevos frescos tipo AA',16500.00,5.00,'94','999',60,1,'2026-11-04 17:37:16'),
(9,'BED-006','Aceite girasol 1L','Aceite vegetal',9200.00,19.00,'94','999',85,1,'2026-11-04 17:37:16'),
(10,'BED-007','Azucar blanca 1kg','Azucar refinada',4800.00,19.00,'94','999',100,1,'2026-11-04 17:37:16'),
(11,'BED-008','Sal marina 500g','Sal refinada',2200.00,19.00,'94','999',150,1,'2026-11-04 17:37:16'),
(12,'BED-009','Harina de trigo 1kg','Multiproposito',3900.00,19.00,'94','999',95,1,'2026-11-04 17:37:16'),
(13,'BED-010','Pasta espagueti 500g','Pasta trigo duro',3200.00,19.00,'94','999',130,1,'2026-11-04 17:37:16'),
(14,'BED-011','Atun en aceite 300g','Conserva',6900.00,19.00,'94','999',85,1,'2026-11-04 17:37:16'),
(15,'BED-012','Frijol blanco 500g','Legumbre',4700.00,19.00,'94','999',75,1,'2026-11-04 17:37:16'),
(16,'BED-013','Lentejas 500g','Legumbre',4200.00,19.00,'94','999',75,1,'2026-11-04 17:37:16'),
(17,'BED-014','Cafe instantaneo 100g','Soluble',8900.00,19.00,'94','999',70,1,'2026-11-04 17:37:16'),
(18,'BED-015','Galletas saladas 250g','Snack horneado',3100.00,19.00,'94','999',140,1,'2026-11-04 17:37:16'),
(19,'BED-016','Chocolate en polvo 400g','Bebible',7500.00,19.00,'94','999',65,1,'2026-11-04 17:37:16'),
(20,'BED-017','Shampoo 400ml','Cuidado personal',11800.00,19.00,'94','999',55,1,'2026-11-04 17:37:16'),
(21,'BED-018','Jabon corporal 250g','Cuidado personal',5200.00,19.00,'94','999',100,1,'2026-11-04 17:37:16'),
(22,'BED-019','Crema dental 100ml','Higiene',6300.00,19.00,'94','999',110,1,'2026-11-04 17:37:16'),
(23,'BED-020','Papel higienico x4','Higiene hogar',7400.00,19.00,'94','999',120,1,'2026-11-04 17:37:16'),
(24,'BED-021','Detergente 1kg','Aseo',9600.00,19.00,'94','999',80,1,'2026-11-04 17:37:16'),
(25,'BED-022','Jabon de barra x3','Aseo',4100.00,19.00,'94','999',125,1,'2026-11-04 17:37:16'),
(26,'BED-023','Agua sin gas 600ml','Hidratacion',1900.00,19.00,'94','999',247,1,'2026-11-04 17:37:16'),
(27,'BED-024','Gaseosa 1.5L','Bebida',5800.00,19.00,'94','999',150,1,'2026-11-04 17:37:16'),
(28,'BED-025','Malta 355ml','Bebida',3400.00,19.00,'94','999',140,1,'2026-11-04 17:37:16'),
(29,'BED-026','Snack de papas 150g','Snack',4600.00,19.00,'94','999',160,1,'2026-11-04 17:37:16'),
(30,'BED-027','Pan artesanal 500g','Panaderia',5300.00,5.00,'94','999',40,1,'2026-11-04 17:37:16'),
(31,'BED-028','Queso campesino 400g','Lacteo fresco',9900.00,5.00,'94','999',45,1,'2026-11-04 17:37:16'),
(32,'BED-029','Mortadela 500g','Frio',7800.00,5.00,'94','999',50,1,'2026-11-04 17:37:16'),
(33,'BED-030','Avena en hojuelas 500g','Cereal',4400.00,0.00,'94','999',90,1,'2026-11-04 17:37:16'),
(34,'BED-031','Miel pura 500g','Endulzante natural',13800.00,0.00,'94','999',40,1,'2026-11-04 17:37:16'),
(35,'BED-032','Quinoa 500g','Grano andino',7600.00,19.00,'94','999',45,1,'2026-11-04 17:37:16');
/*!40000 ALTER TABLE `productos` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*M!100616 SET NOTE_VERBOSITY=@OLD_NOTE_VERBOSITY */;

