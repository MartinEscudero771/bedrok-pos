import os
import mysql.connector


def conectar():
    try:
        config = {
            "host": os.getenv("DB_HOST"),
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD"),
            "database": os.getenv("DB_NAME"),
        }
        if not all(config.values()):
            print("Faltan variables de configuracion de MySQL en el archivo .env")
            return None
        return mysql.connector.connect(**config)
    except mysql.connector.Error as error:
        print("Error al conectar con MySQL:", error)
        return None


def init_db():
    """Crea tablas base + migraciones POS/Factus Pay. Idempotente."""
    con = conectar()
    if not con:
        return False
    cur = con.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS clientes (
                id_cliente INT AUTO_INCREMENT PRIMARY KEY,
                tipo_documento VARCHAR(10) NOT NULL,
                numero_documento VARCHAR(30) NOT NULL UNIQUE,
                nombres VARCHAR(200) NOT NULL,
                direccion VARCHAR(250) DEFAULT '',
                telefono VARCHAR(30) DEFAULT '',
                correo VARCHAR(150) DEFAULT '',
                codigo_organizacion VARCHAR(5) DEFAULT '2',
                codigo_tributo VARCHAR(5) DEFAULT 'ZZ',
                codigo_pais VARCHAR(5) DEFAULT 'CO',
                codigo_municipio VARCHAR(10) DEFAULT '23001',
                activo TINYINT(1) DEFAULT 1,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS productos (
                id_producto INT AUTO_INCREMENT PRIMARY KEY,
                codigo_referencia VARCHAR(50) NOT NULL UNIQUE,
                nombre VARCHAR(150) NOT NULL,
                descripcion VARCHAR(250) DEFAULT '',
                precio DECIMAL(14,2) NOT NULL,
                porcentaje_iva DECIMAL(5,2) NOT NULL DEFAULT 19.00,
                codigo_unidad VARCHAR(10) DEFAULT '94',
                codigo_estandar VARCHAR(10) DEFAULT '999',
                stock INT NOT NULL DEFAULT 0,
                activo TINYINT(1) DEFAULT 1,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS facturas (
                id_factura INT AUTO_INCREMENT PRIMARY KEY,
                id_cliente INT NOT NULL,
                codigo_referencia VARCHAR(100) NOT NULL UNIQUE,
                fecha_emision DATETIME DEFAULT CURRENT_TIMESTAMP,
                subtotal DECIMAL(14,2) NOT NULL DEFAULT 0,
                total_iva DECIMAL(14,2) NOT NULL DEFAULT 0,
                total DECIMAL(14,2) NOT NULL DEFAULT 0,
                estado VARCHAR(20) DEFAULT 'PENDIENTE',
                ambiente VARCHAR(20) DEFAULT 'SANDBOX',
                cufe VARCHAR(250) NULL,
                numero_factura VARCHAR(50) NULL,
                url_pdf TEXT NULL,
                metodo_pago VARCHAR(20) DEFAULT 'EFECTIVO',
                pay_reference VARCHAR(100) NULL,
                pay_status VARCHAR(20) DEFAULT 'SIN_QR',
                FOREIGN KEY (id_cliente) REFERENCES clientes(id_cliente)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS detalle_factura (
                id_detalle INT AUTO_INCREMENT PRIMARY KEY,
                id_factura INT NOT NULL,
                id_producto INT NOT NULL,
                cantidad INT NOT NULL,
                precio_unitario DECIMAL(14,2) NOT NULL,
                porcentaje_iva DECIMAL(5,2) NOT NULL,
                valor_iva DECIMAL(14,2) NOT NULL,
                subtotal DECIMAL(14,2) NOT NULL,
                total DECIMAL(14,2) NOT NULL,
                FOREIGN KEY (id_factura) REFERENCES facturas(id_factura) ON DELETE CASCADE,
                FOREIGN KEY (id_producto) REFERENCES productos(id_producto)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS respuestas_factus (
                id_respuesta INT AUTO_INCREMENT PRIMARY KEY,
                id_factura INT NULL,
                codigo_referencia VARCHAR(100) NULL,
                codigo_http INT NULL,
                estado_api VARCHAR(20) NULL,
                mensaje TEXT NULL,
                solicitud_json MEDIUMTEXT NULL,
                respuesta_json MEDIUMTEXT NULL,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (id_factura) REFERENCES facturas(id_factura) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS recaudos_pay (
                id_recaudo INT AUTO_INCREMENT PRIMARY KEY,
                id_factura INT NULL,
                reference_code VARCHAR(100) NOT NULL UNIQUE,
                amount DECIMAL(14,2) NOT NULL,
                status VARCHAR(20) DEFAULT 'ready',
                breb_key VARCHAR(100) NULL,
                qr LONGTEXT NULL,
                qr_expires_at VARCHAR(50) NULL,
                collected_at VARCHAR(50) NULL,
                payer_json TEXT NULL,
                raw_json MEDIUMTEXT NULL,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (id_factura) REFERENCES facturas(id_factura) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS webhook_logs (
                id_log INT AUTO_INCREMENT PRIMARY KEY,
                reference_code VARCHAR(100) NULL,
                payload MEDIUMTEXT NULL,
                resultado VARCHAR(250) NULL,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        for ddl in [
            "ALTER TABLE facturas ADD COLUMN IF NOT EXISTS metodo_pago VARCHAR(20) DEFAULT 'EFECTIVO'",
            "ALTER TABLE facturas ADD COLUMN IF NOT EXISTS pay_reference VARCHAR(100) NULL",
            "ALTER TABLE facturas ADD COLUMN IF NOT EXISTS pay_status VARCHAR(20) DEFAULT 'SIN_QR'",
            "ALTER TABLE facturas ADD COLUMN IF NOT EXISTS cufe VARCHAR(250) NULL",
            "ALTER TABLE facturas ADD COLUMN IF NOT EXISTS numero_factura VARCHAR(50) NULL",
            "ALTER TABLE facturas ADD COLUMN IF NOT EXISTS url_pdf TEXT NULL",
            "ALTER TABLE facturas ADD COLUMN IF NOT EXISTS moneda VARCHAR(5) NULL",
            "ALTER TABLE facturas ADD COLUMN IF NOT EXISTS tasa_cambio DECIMAL(13,4) NULL",
            "ALTER TABLE facturas ADD COLUMN IF NOT EXISTS monto_moneda DECIMAL(14,2) NULL",
            "ALTER TABLE facturas ADD COLUMN IF NOT EXISTS cambio_moneda DECIMAL(14,2) NULL",
            "ALTER TABLE productos ADD COLUMN IF NOT EXISTS codigo_unidad VARCHAR(10) DEFAULT '94'",
            "ALTER TABLE productos ADD COLUMN IF NOT EXISTS codigo_estandar VARCHAR(10) DEFAULT '999'",
            "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS codigo_organizacion VARCHAR(5) DEFAULT '2'",
            "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS codigo_tributo VARCHAR(5) DEFAULT 'ZZ'",
            "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS codigo_pais VARCHAR(5) DEFAULT 'CO'",
            "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS codigo_municipio VARCHAR(10) DEFAULT '23001'",
        ]:
            try:
                cur.execute(ddl)
            except Exception:
                pass
        con.commit()
        return True
    except Exception as e:
        print("init_db error:", e)
        try:
            con.rollback()
        except Exception:
            pass
        return False
    finally:
        try:
            cur.close()
            con.close()
        except Exception:
            pass
