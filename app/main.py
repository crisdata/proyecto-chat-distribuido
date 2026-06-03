# main.py
# Punto de entrada del sistema.
# Configura la aplicación, registra los routers y gestiona
# el ciclo de vida de las conexiones a MariaDB, Redis, Ollama y RabbitMQ.

import asyncio
import logging
import os
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager

from app.logging_config import configurar_logging

# Configurar logging ANTES de importar cualquier otro módulo de la app,
# para que todos los módulos vean el formato configurado al cargar
# sus propios loggers a nivel de módulo.
configurar_logging()

from app.routers import usuarios, mensajes, ia, websocket
from app.routers.grupos import router as grupos_router  # pyright: ignore[reportMissingImports]
from app.routers.interno import router as interno_router
from app.routers.ia import registrar_nodo_ia
from app.database import conectar, desconectar, crear_tablas, get_connection, release_connection
from app.cache import conectar_redis, desconectar_redis
from app.queue import conectar_queue, desconectar_queue
from app.request_id import (
    set_request_id,
    generar_request_id,
    get_request_id,
)

log = logging.getLogger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestiona el ciclo de vida de la aplicación.
    Al arrancar: conecta Redis, MariaDB, registra nodo IA, conecta RabbitMQ.
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

    # Pre-calentar el modelo de IA en background para no bloquear el arranque.
    # Si falla, no es crítico: el primer mensaje usará fallback empático.
    log.info("Lanzando pre-calentamiento de Lumi en background")
    from app.routers.ia import precalentar_modelo
    asyncio.create_task(precalentar_modelo())

    # Tarea de limpieza: elimina mensajes autodestructivos expirados cada 30s
    async def limpiar_mensajes_expirados():
        while True:
            await asyncio.sleep(30)
            try:
                conn = await get_connection()
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        "DELETE FROM mensajes WHERE expira_en IS NOT NULL AND expira_en <= NOW()"
                    )
                    eliminados = cursor.rowcount
                    if eliminados > 0:
                        log.info(f"Limpieza: {eliminados} mensaje(s) autodestructivo(s) eliminado(s)")
                await release_connection(conn)
            except Exception as e:
                log.warning(f"Error en limpieza de mensajes expirados: {e}")

    asyncio.create_task(limpiar_mensajes_expirados())

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


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """
    Middleware que gestiona el request_id de cada petición HTTP.
    
    Flujo:
      1. Si el cliente envía el header X-Request-ID, lo respetamos
         (útil cuando el worker propaga el ID en sus llamadas internas).
      2. Si no, generamos uno nuevo.
      3. Lo establecemos en el ContextVar para que todos los logs
         de esta petición lo lleven automáticamente.
      4. Después de procesar, lo devolvemos al cliente en el header
         de respuesta para que pueda usarlo si lo necesita.
    """
    # Aceptar request_id entrante si el cliente (típicamente el worker
    # o un cliente HTTP que ya está en una cadena) lo propaga.
    rid_entrante = request.headers.get("X-Request-ID")
    request_id = rid_entrante if rid_entrante else generar_request_id()

    set_request_id(request_id)

    # Procesar la petición normalmente
    response = await call_next(request)

    # Devolver el request_id al cliente para que pueda referenciarlo
    response.headers["X-Request-ID"] = request_id

    return response


app.include_router(usuarios.router)
app.include_router(mensajes.router)
app.include_router(ia.router)
app.include_router(websocket.router)
app.include_router(grupos_router)
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