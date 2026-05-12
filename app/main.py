# main.py
# Punto de entrada del sistema.
# Configura la aplicación, registra los routers y gestiona
# el ciclo de vida de las conexiones a MariaDB, Redis, Ollama y RabbitMQ.

import logging
import os
from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.logging_config import configurar_logging

# Configurar logging ANTES de importar cualquier otro módulo de la app,
# para que todos los módulos vean el formato configurado al cargar
# sus propios loggers a nivel de módulo.
configurar_logging()

from app.routers import usuarios, mensajes, ia, websocket
from app.routers.interno import router as interno_router
from app.routers.ia import registrar_nodo_ia
from app.database import conectar, desconectar, crear_tablas
from app.cache import conectar_redis, desconectar_redis
from app.queue import conectar_queue, desconectar_queue

log = logging.getLogger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestiona el ciclo de vida de la aplicación.
    Al arrancar:
      1. Conecta a Redis
      2. Conecta a MariaDB
      3. Crea las tablas si no existen
      4. Registra el nodo IA como usuario del sistema
      5. Conecta a RabbitMQ
    Al apagar: cierra todas las conexiones en orden inverso.
    """
    log.info("Arrancando API")

    log.info("Conectando a Redis")
    await conectar_redis()

    log.info("Conectando a MariaDB")
    await conectar()

    log.info("Verificando tablas")
    await crear_tablas()

    log.info("Registrando nodo IA")
    await registrar_nodo_ia()

    log.info("Conectando a RabbitMQ")
    await conectar_queue()

    log.info("API lista para recibir solicitudes")

    yield

    log.info("Apagando API")
    await desconectar()
    await desconectar_redis()
    await desconectar_queue()
    log.info("API apagada limpiamente")


app = FastAPI(
    title="Chat Privado Usuario-Usuario",
    description=(
        "Sistema de chat distribuido con comunicación privada entre usuarios "
        "y nodo de inteligencia artificial local (Ollama llama3.2:3b). "
    ),
    version="3.0.0",
    lifespan=lifespan
)

app.include_router(usuarios.router)
app.include_router(mensajes.router)
app.include_router(ia.router)
app.include_router(websocket.router)
app.include_router(interno_router)


@app.get("/", tags=["Estado"])
async def estado():
    """Verifica que el servidor está en línea."""
    return {
        "sistema": "Chat Privado Usuario-Usuario",
        "version": "3.0.0",
        "estado": "en línea",
        "infraestructura": {
            "base_de_datos": "MariaDB",
            "cache": "Redis",
            "ia": f"Ollama {os.getenv('OLLAMA_MODEL', 'llama3.2:3b')}",
            "tiempo_real": "WebSocket",
            "mensajeria": "RabbitMQ"
        }
    }