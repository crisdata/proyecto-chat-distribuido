# routers/interno.py
# Endpoints internos usados exclusivamente por el worker.
#
# Aunque la API está en public_network y este endpoint es alcanzable
# desde el exterior a través de Nginx, está protegido por un secreto
# compartido (WORKER_SECRET) que solo conocen el worker y la API.
# Cualquier request sin el header X-Worker-Secret correcto recibe 403.
#
# El worker propaga el request_id original via header X-Request-ID,
# que el middleware HTTP de la API ya está configurado para respetar.
# Esto cierra el ciclo de trazabilidad: el mismo ID aparece en los
# logs de la API, RabbitMQ, el worker, y de vuelta en este endpoint.

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.routers.websocket import manager
from app.cache import incrementar_no_leidos_de
from app.auth import autenticar_worker

router = APIRouter(prefix="/interno", tags=["Interno"])
log = logging.getLogger("interno")


class EventoMensaje(BaseModel):
    """Estructura del evento que el worker envía para notificar."""
    receptor_id: str
    emisor_id: str
    emisor_nombre: str


@router.post("/notificar", dependencies=[Depends(autenticar_worker)])
async def notificar_receptor(evento: EventoMensaje):
    """
    Recibe una notificación del worker y la reenvía al receptor
    via WebSocket si está conectado.
    Incrementa el contador específico de no leídos entre el receptor
    y el emisor, para que el frontend pueda mostrar un badge individual
    por contacto.

    El request_id propagado por el worker via header X-Request-ID
    aparece automáticamente en los logs de este endpoint gracias
    al middleware HTTP, cerrando el ciclo de trazabilidad.
    """
    log.info(
        f"Notificación recibida del worker: "
        f"{evento.emisor_nombre} → {evento.receptor_id}"
    )

    # Incrementar contador específico de la pareja receptor+emisor.
    # El frontend usa este valor para mostrar el badge individual
    # junto a cada contacto en la lista.
    await incrementar_no_leidos_de(evento.receptor_id, evento.emisor_id)

    # Notificar via WebSocket si el receptor está conectado.
    # El evento incluye el emisor_id para que el frontend pueda
    # actualizar el badge específico de ese contacto inmediatamente.
    await manager.notify(evento.receptor_id, {
        "tipo": "nuevo_mensaje",
        "emisor_id": evento.emisor_id,
        "emisor_nombre": evento.emisor_nombre
    })

    conectado = manager.esta_conectado(evento.receptor_id)
    log.info(
        f"Notificación entregada al WebSocket: "
        f"receptor {'conectado' if conectado else 'offline'}"
    )

    return {"ok": True}