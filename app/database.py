# database.py
# Gestiona la conexión a MariaDB y la creación de tablas.
# Usa aiomysql para conexiones asíncronas, coherente con FastAPI.

import aiomysql
import os
from dotenv import load_dotenv

load_dotenv()

# Configuración de la base de datos desde variables de entorno
DB_CONFIG = {
    "host": "db",
    "port": 3306,
    "user": os.getenv("MYSQL_USER"),
    "password": os.getenv("MYSQL_PASSWORD"),
    "db": os.getenv("MYSQL_DATABASE"),
    "autocommit": True,
}

# Pool de conexiones compartido por toda la aplicación
pool = None


async def conectar():
    """Crea el pool de conexiones al iniciar la aplicación."""
    global pool
    pool = await aiomysql.create_pool(**DB_CONFIG)


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
    """
    conn = await get_connection()
    try:
        async with conn.cursor() as cursor:

            # Tabla de usuarios registrados en el sistema
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id VARCHAR(36) PRIMARY KEY,
                    nombre VARCHAR(100) NOT NULL UNIQUE,
                    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Tabla de mensajes privados entre usuarios
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS mensajes (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    emisor_id VARCHAR(36) NOT NULL,
                    receptor_id VARCHAR(36) NOT NULL,
                    contenido TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (emisor_id) REFERENCES usuarios(id),
                    FOREIGN KEY (receptor_id) REFERENCES usuarios(id)
                )
            """)
    finally:
        await release_connection(conn)# database.py
# Gestiona la conexión a MariaDB y la creación de tablas.
# Usa aiomysql para conexiones asíncronas, coherente con FastAPI.

import aiomysql
import os
from dotenv import load_dotenv

load_dotenv()

# Configuración de la base de datos desde variables de entorno
DB_CONFIG = {
    "host": "db",
    "port": 3306,
    "user": os.getenv("MYSQL_USER"),
    "password": os.getenv("MYSQL_PASSWORD"),
    "db": os.getenv("MYSQL_DATABASE"),
    "autocommit": True,
}

# Pool de conexiones compartido por toda la aplicación
pool = None


async def conectar():
    """Crea el pool de conexiones al iniciar la aplicación."""
    global pool
    pool = await aiomysql.create_pool(**DB_CONFIG)


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
                    nombre VARCHAR(100) NOT NULL UNIQUE,
                    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Tabla de mensajes privados entre usuarios.
            # Los índices aceleran las consultas más frecuentes del sistema:
            # idx_receptor    → GET /conversacion/{usuario_id}
            # idx_emisor      → consultas por historial enviado
            # idx_conversacion → conversación entre dos usuarios específicos
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS mensajes (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    emisor_id VARCHAR(36) NOT NULL,
                    receptor_id VARCHAR(36) NOT NULL,
                    contenido TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (emisor_id) REFERENCES usuarios(id),
                    FOREIGN KEY (receptor_id) REFERENCES usuarios(id),
                    INDEX idx_receptor (receptor_id),
                    INDEX idx_emisor (emisor_id),
                    INDEX idx_conversacion (emisor_id, receptor_id)
                )
            """)
    finally:
        await release_connection(conn)
