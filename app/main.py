# main.py
# Punto de entrada del sistema.
# Configura la aplicación, registra los routers y gestiona
# el ciclo de vida de las conexiones a MariaDB y Redis.

from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.routers import usuarios, mensajes
from app.database import conectar, desconectar, crear_tablas
from app.cache import conectar_redis, desconectar_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestiona el ciclo de vida de la aplicación.
    Al arrancar: conecta a MariaDB y Redis, crea las tablas.
    Al apagar: cierra todas las conexiones limpiamente.
    """
    # Arranque
    await conectar_redis()
    await conectar()
    await crear_tablas()
    yield
    # Apagado
    await desconectar()
    await desconectar_redis()


app = FastAPI(
    title="Chat Privado Usuario-Usuario",
    description=(
        "Sistema de chat distribuido con comunicación privada entre usuarios "
        "y nodo de inteligencia artificial local. "
    ),
    version="2.0.0",
    lifespan=lifespan
)

# Registrar routers
app.include_router(usuarios.router)
app.include_router(mensajes.router)


@app.get("/", tags=["Estado"])
async def estado():
    """Verifica que el servidor está en línea."""
    return {
        "sistema": "Chat Privado Usuario-Usuario",
        "version": "2.0.0",
        "estado": "en línea",
        "infraestructura": {
            "base_de_datos": "MariaDB",
            "cache": "Redis",
            "ia": "Ollama llama3.2:3b"
        }
    }