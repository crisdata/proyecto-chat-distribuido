# main.py
# Punto de entrada del sistema.
# Aquí se configura la aplicación y se registran los routers.

from fastapi import FastAPI
from app.routers import usuarios, mensajes

# Información general del sistema que aparece en la documentación automática.
app = FastAPI(
    title="Chat Privado Usuario-Usuario",
    description=(
        "Sistema de chat distribuido que permite la comunicación privada "
        "entre usuarios registrados. Proyecto Grupo 4 — COTECNOVA."
    ),
    version="1.0.0"
)

# Registrar los routers con sus respectivos endpoints.
app.include_router(usuarios.router)
app.include_router(mensajes.router)


# Endpoint raíz para verificar que el servidor está funcionando.
@app.get("/", tags=["Estado"])
async def estado():
    """
    Verifica que el servidor está en línea.
    """
    return {
        "sistema": "Chat Privado Usuario-Usuario",
        "estado": "en línea",
        "version": "1.0.0"
    }
