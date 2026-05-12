# routers/ia.py
# Gestiona el nodo de inteligencia artificial como participante del chat.
# Ollama se registra como usuario al arrancar el servidor y responde
# mensajes usando el mismo protocolo que cualquier usuario humano.
#
# Endpoints disponibles:
#   POST /ia/mensaje  — enviar mensaje directo al nodo IA
#   GET  /ia/estado   — verificar disponibilidad del nodo IA

import uuid
import os
from fastapi import APIRouter, HTTPException
from ollama import AsyncClient
from dotenv import load_dotenv
from app.models import MensajeCreate, MensajeResponse, RespuestaExito
from app.database import get_connection, release_connection
from app.cache import (
    cachear_usuario,
    get_redis
)
from app.queue import publicar

load_dotenv()

router = APIRouter(prefix="/ia", tags=["Inteligencia Artificial"])

# Nombre del nodo IA visible en el chat para todos los usuarios
NOMBRE_IA = "Asistente IA"
MODELO_IA = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_URL = f"http://{os.getenv('OLLAMA_HOST', 'ollama')}:{os.getenv('OLLAMA_PORT', '11434')}"


async def obtener_id_ia() -> str | None:
    """
    Obtiene el ID del nodo IA desde Redis.
    Retorna None si el nodo aún no ha sido registrado.
    """
    redis = get_redis()
    return await redis.get("ia:id")


async def registrar_nodo_ia():
    """
    Registra el nodo IA como usuario del sistema si no existe.
    Se llama una vez al arrancar el servidor desde main.py.
    """
    conn = await get_connection()
    try:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "SELECT id FROM usuarios WHERE nombre = %s",
                (NOMBRE_IA,)
            )
            existente = await cursor.fetchone()

            if existente:
                ia_id = existente[0]
            else:
                ia_id = str(uuid.uuid4())
                await cursor.execute(
                    "INSERT INTO usuarios (id, nombre) VALUES (%s, %s)",
                    (ia_id, NOMBRE_IA)
                )

        redis = get_redis()
        await redis.set("ia:id", ia_id)
        await cachear_usuario(ia_id, NOMBRE_IA, ttl=86400)

        return ia_id

    finally:
        await release_connection(conn)


async def generar_respuesta_ia(mensaje: str, historial: list) -> str:
    """
    Envía el mensaje a Ollama con el historial reciente como contexto.
    El historial llega ya limitado a los últimos 10 mensajes en orden
    cronológico ascendente desde el llamador.
    Lanza HTTPException 503 si Ollama no está disponible.
    """
    cliente = AsyncClient(host=OLLAMA_URL)

    mensajes = [
        {
            "role": "system",
            "content": (
                "Eres un asistente útil dentro de un sistema de chat distribuido. "
                "Responde de forma clara, concisa y en el mismo idioma del usuario. "
                "Eres un participante más del chat, no un asistente externo."
            )
        }
    ]

    for h in historial:
        mensajes.append({
            "role": "user" if h["es_usuario"] else "assistant",
            "content": h["contenido"]
        })

    mensajes.append({"role": "user", "content": mensaje})

    try:
        respuesta = await cliente.chat(
            model=MODELO_IA,
            messages=mensajes
        )
        return respuesta.message.content
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"El nodo IA no está disponible en este momento: {str(e)}"
        )


@router.post("/mensaje", response_model=MensajeResponse, status_code=201)
async def mensaje_a_ia(datos: MensajeCreate):
    """
    Envía un mensaje al nodo IA y retorna su respuesta.
    Usa los 10 mensajes más recientes de la conversación como contexto
    para mantener coherencia entre turnos.

    Después de persistir la respuesta, publica un evento en RabbitMQ
    para que el worker notifique al usuario via WebSocket. Esto garantiza
    que si el usuario tiene el chat abierto en otra pestaña o dispositivo,
    también vea la respuesta de la IA en tiempo real.
    """
    conn = await get_connection()
    try:
        # Verificar que el emisor existe
        async with conn.cursor() as cursor:
            await cursor.execute(
                "SELECT id FROM usuarios WHERE id = %s",
                (datos.emisor_id,)
            )
            if not await cursor.fetchone():
                raise HTTPException(
                    status_code=404,
                    detail="El usuario no existe. Verifica el emisor_id."
                )

        # Obtener ID del nodo IA desde Redis
        ia_id = await obtener_id_ia()
        if not ia_id:
            raise HTTPException(
                status_code=503,
                detail="El nodo IA no está inicializado. Intenta de nuevo en unos segundos."
            )

        # Obtener los 10 mensajes MÁS RECIENTES de la conversación
        # entre el usuario y la IA. Usamos DESC LIMIT 10 para sacar los
        # recientes y los reordenamos cronológicamente con la subconsulta
        # para que el modelo los lea en orden de viejo a nuevo.
        async with conn.cursor() as cursor:
            await cursor.execute(
                """SELECT emisor_id, contenido FROM (
                       SELECT emisor_id, contenido, timestamp
                       FROM mensajes
                       WHERE (emisor_id = %s AND receptor_id = %s)
                          OR (emisor_id = %s AND receptor_id = %s)
                       ORDER BY timestamp DESC
                       LIMIT 10
                   ) sub
                   ORDER BY timestamp ASC""",
                (datos.emisor_id, ia_id, ia_id, datos.emisor_id)
            )
            historial_raw = await cursor.fetchall()

        historial = [
            {
                "es_usuario": h[0] == datos.emisor_id,
                "contenido": h[1]
            }
            for h in historial_raw
        ]

        # Generar respuesta del modelo de IA
        respuesta_texto = await generar_respuesta_ia(datos.contenido, historial)

        async with conn.cursor() as cursor:
            # Persistir el mensaje del usuario
            await cursor.execute(
                """INSERT INTO mensajes (emisor_id, receptor_id, contenido)
                   VALUES (%s, %s, %s)""",
                (datos.emisor_id, ia_id, datos.contenido)
            )

            # Persistir la respuesta de la IA
            await cursor.execute(
                """INSERT INTO mensajes (emisor_id, receptor_id, contenido)
                   VALUES (%s, %s, %s)""",
                (ia_id, datos.emisor_id, respuesta_texto)
            )
            respuesta_id = cursor.lastrowid

            await cursor.execute(
                """SELECT id, emisor_id, receptor_id, contenido, timestamp
                   FROM mensajes WHERE id = %s""",
                (respuesta_id,)
            )
            respuesta = await cursor.fetchone()

        # Publicar evento en RabbitMQ para notificar al usuario en
        # cualquier otra pestaña o dispositivo donde tenga el chat abierto.
        # El emisor es la IA, el receptor es el usuario humano.
        # Si RabbitMQ falla, el response HTTP ya devuelve la respuesta,
        # solo se pierde la notificación a otras pestañas.
        await publicar("mensajes", {
            "receptor_id": datos.emisor_id,
            "emisor_id": ia_id,
            "emisor_nombre": NOMBRE_IA
        })

        return {
            "id": respuesta[0],
            "emisor_id": respuesta[1],
            "receptor_id": respuesta[2],
            "contenido": respuesta[3],
            "timestamp": respuesta[4].isoformat()
        }

    finally:
        await release_connection(conn)


@router.get("/estado", response_model=RespuestaExito)
async def estado_ia():
    """
    Verifica que el nodo IA está disponible y responde.
    """
    try:
        cliente = AsyncClient(host=OLLAMA_URL)
        await cliente.list()
        ia_id = await obtener_id_ia()
        return {
            "mensaje": f"Nodo IA en línea — modelo: {MODELO_IA} — ID: {ia_id}"
        }
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="El nodo IA no está disponible en este momento."
        )