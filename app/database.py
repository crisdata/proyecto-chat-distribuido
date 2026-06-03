# database.py
# Gestiona la conexión a MariaDB y la creación de tablas.
# Usa aiomysql para conexiones asíncronas, coherente con FastAPI.

import asyncio
import logging
import aiomysql  # type: ignore[import-untyped]
import os
from typing import Any
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger("database")

# Configuración de la base de datos desde variables de entorno
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "db"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("MYSQL_USER"),
    "password": os.getenv("MYSQL_PASSWORD"),
    "db": os.getenv("MYSQL_DATABASE"),
    "autocommit": True,
}

# Pool de conexiones compartido por toda la aplicación
pool: Any = None


async def conectar():
    """
    Crea el pool de conexiones al iniciar la aplicación.

    Implementa reintentos con espera para tolerar arranques lentos de
    MariaDB. En equipos modestos, MariaDB puede tomar 20-30 segundos en
    estar listo para aceptar conexiones, especialmente en el primer
    arranque cuando inicializa el volumen de datos. La función incluye
    una validación con SELECT 1 antes de marcar la conexión como exitosa.
    """
    global pool

    intentos_maximos = 10
    espera_entre_intentos = 3  # segundos

    for intento in range(1, intentos_maximos + 1):
        try:
            log.info(
                f"Intento {intento}/{intentos_maximos} de conexión a MariaDB..."
            )
            pool = await aiomysql.create_pool(**DB_CONFIG)

            # Validación con SELECT 1 para confirmar conexión real,
            # no solo que el pool se haya creado.
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1")
                    await cur.fetchone()

            log.info("Conexión a MariaDB establecida correctamente")
            return

        except Exception as e:
            if intento == intentos_maximos:
                log.error(
                    f"Imposible conectar a MariaDB tras "
                    f"{intentos_maximos} intentos. Último error: {e}"
                )
                raise RuntimeError(
                    f"No se pudo conectar a MariaDB tras {intentos_maximos} "
                    f"intentos. ¿Las credenciales del .env coinciden con el "
                    f"volumen db_data? Si no, ejecuta: "
                    f"docker compose -f docker-compose.prod.yml down -v"
                ) from e

            log.warning(
                f"Intento {intento} falló ({type(e).__name__}: {e}). "
                f"Reintentando en {espera_entre_intentos}s..."
            )
            await asyncio.sleep(espera_entre_intentos)


async def desconectar():
    """Cierra el pool de conexiones al apagar la aplicación."""
    global pool
    if pool:
        pool.close()
        await pool.wait_closed()


async def get_connection():
    """Retorna una conexión del pool para ejecutar consultas."""
    return await pool.acquire()


async def release_connection(conn):
    """Devuelve la conexión al pool después de usarla."""
    pool.release(conn)


async def crear_tablas():
    """
    Crea las tablas necesarias si no existen.
    Se ejecuta una sola vez al arrancar el servidor.
    Los índices garantizan consultas eficientes bajo carga.
    """
    conn = await get_connection()
    try:
        async with conn.cursor() as cursor:

            # Tabla de usuarios registrados en el sistema
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id VARCHAR(36) PRIMARY KEY,
                    email VARCHAR(255) NULL UNIQUE,
                    nombre VARCHAR(100) NOT NULL,
                    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_usuarios_nombre (nombre)
                )
            """)

            # Migración: agregar email para login demo si la tabla ya existía.
            try:
                await cursor.execute("""
                    ALTER TABLE usuarios ADD COLUMN email VARCHAR(255) NULL
                """)
            except Exception:
                pass  # Ya existe, ignorar

            # Migración: índice único sobre email normalizado.
            try:
                await cursor.execute("""
                    ALTER TABLE usuarios ADD UNIQUE INDEX uq_usuarios_email (email)
                """)
            except Exception:
                pass  # Ya existe o hay motor que reporta duplicado, ignorar

            # Migración: nombre deja de ser identidad única; email/id son identidad.
            try:
                await cursor.execute("""
                    ALTER TABLE usuarios DROP INDEX nombre
                """)
            except Exception:
                pass  # El índice no existe o ya fue removido

            # Tabla de mensajes privados entre usuarios.
            # Los índices aceleran las consultas más frecuentes del sistema:
            # idx_receptor     → GET /conversacion/{usuario_id}
            # idx_emisor       → consultas por historial enviado
            # idx_conversacion → conversación entre dos usuarios específicos
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS mensajes (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    emisor_id VARCHAR(36) NOT NULL,
                    receptor_id VARCHAR(36) NOT NULL,
                    contenido TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expira_en TIMESTAMP NULL DEFAULT NULL,
                    FOREIGN KEY (emisor_id) REFERENCES usuarios(id),
                    FOREIGN KEY (receptor_id) REFERENCES usuarios(id),
                    INDEX idx_receptor (receptor_id),
                    INDEX idx_emisor (emisor_id),
                    INDEX idx_conversacion (emisor_id, receptor_id)
                )
            """)

            # Migración: agregar columna expira_en si no existe (para BD existentes)
            try:
                await cursor.execute("""
                    ALTER TABLE mensajes ADD COLUMN expira_en TIMESTAMP NULL DEFAULT NULL
                """)
            except Exception:
                pass  # Ya existe, ignorar
    finally:
        await release_connection(conn)