# routers/interno.py
# Endpoints internos usados exclusivamente por el worker.
# No están expuestos al exterior — solo son accesibles dentro
# de la red Docker app_network.
#
# El worker no puede acceder directamente al ConnectionManager
# porque vive en un proceso separado con memoria independiente.
# En cambio llama a este endpoint para que la API ejecute
# la notificación WebSocket en su propio proceso.

from fastapi import APIRouter
from pydantic import BaseModel
from app.routers.websocket import manager
from app.cache import incrementar_mensajes_no_leidos

router = APIRouter(prefix="/interno", tags=["Interno"])


class EventoMensaje(BaseModel):
    """Estructura del evento que el worker envía para notificar."""
    receptor_id: str
    emisor_id: str
    emisor_nombre: str


@router.post("/notificar")
async def notificar_receptor(evento: EventoMensaje):
    """
    Recibe una notificación del worker y la reenvía al receptor
    via WebSocket si está conectado.
    También incrementa el contador de no leídos en Redis.
    Este endpoint solo debe ser llamado desde el worker interno.
    """
    # Incrementar contador de no leídos en Redis
    await incrementar_mensajes_no_leidos(evento.receptor_id)

    # Notificar al receptor via WebSocket si está conectado
    await manager.notify(evento.receptor_id, {
        "tipo": "nuevo_mensaje",
        "emisor_id": evento.emisor_id,
        "emisor_nombre": evento.emisor_nombre
    })

    return {"ok": True}