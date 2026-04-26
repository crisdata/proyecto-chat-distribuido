# main.py
# Punto de entrada del sistema.
# Configura la aplicación, registra los routers y gestiona
# el ciclo de vida de las conexiones a MariaDB, Redis y Ollama.

import os
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.routers import usuarios, mensajes, ia, websocket
from app.routers.ia import registrar_nodo_ia
from app.database import conectar, desconectar, crear_tablas
from app.cache import conectar_redis, desconectar_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestiona el ciclo de vida de la aplicación.
    Al arrancar:
      1. Conecta a Redis
      2. Conecta a MariaDB
      3. Crea las tablas si no existen
      4. Registra el nodo IA como usuario del sistema
    Al apagar:
      1. Cierra conexión a MariaDB
      2. Cierra conexión a Redis
    """
    await conectar_redis()
    await conectar()
    await crear_tablas()
    await registrar_nodo_ia()
    yield
    await desconectar()
    await desconectar_redis()


app = FastAPI(
    title="Chat Privado Usuario-Usuario",
    description=(
        "Sistema de chat distribuido con comunicación privada entre usuarios "
        "y nodo de inteligencia artificial local (Ollama llama3.2:3b). "
    ),
    version="3.0.0",
    lifespan=lifespan
)

# Registrar routers en orden lógico
app.include_router(usuarios.router)
app.include_router(mensajes.router)
app.include_router(ia.router)
app.include_router(websocket.router)


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
            "tiempo_real": "WebSocket"
        }
    }