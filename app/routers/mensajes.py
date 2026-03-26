# routers/mensajes.py
# Maneja el envío y consulta de mensajes privados entre usuarios.
# Endpoints disponibles:
#   POST /mensaje_privado
#   GET  /conversacion/{usuario_id}

from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from app.models import MensajeCreate, MensajeResponse
from app.storage import usuarios, conversaciones

router = APIRouter(tags=["Mensajes"])


@router.post("/mensaje_privado", response_model=MensajeResponse, status_code=201)
async def enviar_mensaje(datos: MensajeCreate):
    """
    Envía un mensaje privado de un usuario a otro.
    Ambos usuarios deben estar registrados en el sistema.
    """

    # Verificar que el emisor existe.
    if datos.emisor_id not in usuarios:
        raise HTTPException(
            status_code=404,
            detail="El emisor no existe. Verifica el emisor_id."
        )

    # Verificar que el receptor existe.
    if datos.receptor_id not in usuarios:
        raise HTTPException(
            status_code=404,
            detail="El receptor no existe. Verifica el receptor_id."
        )

    # Construir el objeto del mensaje con marca de tiempo.
    mensaje = {
        "emisor_id": datos.emisor_id,
        "receptor_id": datos.receptor_id,
        "contenido": datos.contenido,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Si el receptor no tiene conversación aún, se crea su lista.
    if datos.receptor_id not in conversaciones:
        conversaciones[datos.receptor_id] = []

    # Guardar el mensaje en el historial del receptor.
    conversaciones[datos.receptor_id].append(mensaje)

    return mensaje


@router.get("/conversacion/{usuario_id}", response_model=list[MensajeResponse])
async def consultar_conversacion(usuario_id: str):
    """
    Devuelve el historial de mensajes recibidos por un usuario.
    Los mensajes están ordenados cronológicamente.
    """

    # Verificar que el usuario existe.
    if usuario_id not in usuarios:
        raise HTTPException(
            status_code=404,
            detail="El usuario no existe. Verifica el usuario_id."
        )

    # Si el usuario existe pero no tiene mensajes, devolver lista vacía.
    return conversaciones.get(usuario_id, [])
