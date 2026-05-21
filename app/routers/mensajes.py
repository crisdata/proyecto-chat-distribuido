# routers/mensajes.py
# Maneja el envío y consulta de mensajes privados entre usuarios.
# Endpoints disponibles:
#   POST /mensaje_privado               — enviar mensaje privado
#   GET  /conversacion/{usuario_id}     — consultar historial recibido
#   GET  /no_leidos/{usuario_id}        — consultar mensajes no leídos
#   GET  /conversacion/{id}/{contacto}  — conversación bilateral completa
#
# Flujo de envío:
#   1. Valida emisor y receptor consultando Redis primero, MariaDB como fallback
#   2. Guarda el mensaje en MariaDB
#   3. Publica evento en RabbitMQ para procesamiento asíncrono
#   4. El worker consume el evento, actualiza Redis y notifica via WebSocket

from fastapi import APIRouter, HTTPException
from app.models import (
    MensajeCreate, MensajeResponse,
    NoLeidosResponse
)
from app.database import get_connection, release_connection
from app.cache import (
    obtener_usuario_cache, cachear_usuario,
    obtener_no_leidos_por_contacto,
    resetear_no_leidos_con,
    resetear_todos_no_leidos
)
from app.queue import publicar
from app.routers.websocket import manager

router = APIRouter(tags=["Mensajes"])


async def validar_usuario(usuario_id: str, conn) -> str | None:
    """
    Verifica que un usuario existe consultando Redis primero.
    Si no está en caché, consulta MariaDB y lo cachea para
    próximas validaciones.
    Retorna el nombre del usuario si existe, None si no existe.
    """
    nombre = await obtener_usuario_cache(usuario_id)
    if nombre:
        return nombre

    async with conn.cursor() as cursor:
        await cursor.execute(
            "SELECT id, nombre FROM usuarios WHERE id = %s",
            (usuario_id,)
        )
        usuario = await cursor.fetchone()

    if not usuario:
        return None

    await cachear_usuario(usuario[0], usuario[1])
    return usuario[1]


@router.post("/mensaje_privado", response_model=MensajeResponse, status_code=201)
async def enviar_mensaje(datos: MensajeCreate):
    """
    Envía un mensaje privado de un usuario a otro.
    Ambos usuarios deben estar registrados en el sistema.
    El mensaje se persiste en MariaDB de forma síncrona garantizada.
    La notificación al receptor se delega al worker via RabbitMQ,
    demostrando el patrón de comunicación desacoplada de la Clase 9.
    """
    conn = await get_connection()
    try:
        # Validar emisor
        nombre_emisor = await validar_usuario(datos.emisor_id, conn)
        if not nombre_emisor:
            raise HTTPException(
                status_code=404,
                detail="El emisor no existe. Verifica el emisor_id."
            )

        # Validar receptor
        nombre_receptor = await validar_usuario(datos.receptor_id, conn)
        if not nombre_receptor:
            raise HTTPException(
                status_code=404,
                detail="El receptor no existe. Verifica el receptor_id."
            )

        # Persistir mensaje en MariaDB de forma síncrona
        # La persistencia nunca se delega — es la fuente de verdad
        async with conn.cursor() as cursor:
            await cursor.execute(
                """INSERT INTO mensajes (emisor_id, receptor_id, contenido)
                   VALUES (%s, %s, %s)""",
                (datos.emisor_id, datos.receptor_id, datos.contenido)
            )
            mensaje_id = cursor.lastrowid

            await cursor.execute(
                """SELECT id, emisor_id, receptor_id, contenido, timestamp
                   FROM mensajes WHERE id = %s""",
                (mensaje_id,)
            )
            mensaje = await cursor.fetchone()

        # Publicar evento en RabbitMQ para procesamiento asíncrono.
        # El worker consume este evento, actualiza Redis y
        # notifica al receptor via WebSocket.
        # Si RabbitMQ no está disponible, el mensaje ya está
        # persistido — solo se pierde la notificación en tiempo real.
        await publicar("mensajes", {
            "receptor_id": datos.receptor_id,
            "emisor_id": datos.emisor_id,
            "emisor_nombre": nombre_emisor
        })

        return {
            "id": mensaje[0],
            "emisor_id": mensaje[1],
            "receptor_id": mensaje[2],
            "contenido": mensaje[3],
            "timestamp": mensaje[4].isoformat()
        }

    finally:
        await release_connection(conn)


@router.get(
    "/conversacion/{usuario_id}",
    response_model=list[MensajeResponse]
)
async def consultar_conversacion(usuario_id: str):
    """
    Retorna el historial de mensajes recibidos por un usuario,
    ordenados cronológicamente.
    Resetea el contador de mensajes no leídos al consultar.
    """
    conn = await get_connection()
    try:
        nombre = await validar_usuario(usuario_id, conn)
        if not nombre:
            raise HTTPException(
                status_code=404,
                detail="El usuario no existe. Verifica el usuario_id."
            )

        async with conn.cursor() as cursor:
            await cursor.execute(
                """SELECT id, emisor_id, receptor_id, contenido, timestamp
                   FROM mensajes
                   WHERE receptor_id = %s
                   ORDER BY timestamp ASC""",
                (usuario_id,)
            )
            mensajes = await cursor.fetchall()

        await resetear_todos_no_leidos(usuario_id)

        return [
            {
                "id": m[0],
                "emisor_id": m[1],
                "receptor_id": m[2],
                "contenido": m[3],
                "timestamp": m[4].isoformat()
            }
            for m in mensajes
        ]

    finally:
        await release_connection(conn)


@router.get(
    "/no_leidos/{usuario_id}",
    response_model=NoLeidosResponse
)
async def mensajes_no_leidos(usuario_id: str):
    """
    Retorna el total de mensajes no leídos del usuario, junto con
    el desglose por contacto. El frontend usa el total para el
    badge global y el desglose para los badges individuales en la lista.

    Estructura:
      {
        "usuario_id": "...",
        "no_leidos": 5,
        "por_contacto": {
          "carlos_uuid": 3,
          "cristian_uuid": 2
        }
      }
    """
    conn = await get_connection()
    try:
        nombre = await validar_usuario(usuario_id, conn)
        if not nombre:
            raise HTTPException(
                status_code=404,
                detail="El usuario no existe. Verifica el usuario_id."
            )

        por_contacto = await obtener_no_leidos_por_contacto(usuario_id)
        total = sum(por_contacto.values())

        return {
            "usuario_id": usuario_id,
            "no_leidos": total,
            "por_contacto": por_contacto
        }

    finally:
        await release_connection(conn)


@router.delete(
    "/no_leidos/{usuario_id}/{contacto_id}",
    status_code=204
)
async def marcar_como_leidos(usuario_id: str, contacto_id: str):
    """
    Borra el contador de mensajes no leídos que el usuario tenía
    con un contacto específico. Se llama cuando el usuario abre
    el chat con ese contacto.

    Retorna 204 No Content si tuvo éxito (sin body).
    """
    await resetear_no_leidos_con(usuario_id, contacto_id)
    return None


@router.get(
    "/conversacion/{usuario_id}/{contacto_id}",
    response_model=list[MensajeResponse]
)
async def consultar_conversacion_bilateral(usuario_id: str, contacto_id: str):
    """
    Retorna el historial completo de mensajes entre dos usuarios,
    en ambas direcciones, ordenados cronológicamente.
    """
    conn = await get_connection()
    try:
        nombre_usuario = await validar_usuario(usuario_id, conn)
        if not nombre_usuario:
            raise HTTPException(
                status_code=404,
                detail="El usuario no existe. Verifica el usuario_id."
            )

        nombre_contacto = await validar_usuario(contacto_id, conn)
        if not nombre_contacto:
            raise HTTPException(
                status_code=404,
                detail="El contacto no existe. Verifica el contacto_id."
            )

        async with conn.cursor() as cursor:
            await cursor.execute(
                """SELECT id, emisor_id, receptor_id, contenido, timestamp
                   FROM mensajes
                   WHERE (emisor_id = %s AND receptor_id = %s)
                      OR (emisor_id = %s AND receptor_id = %s)
                   ORDER BY timestamp ASC""",
                (usuario_id, contacto_id, contacto_id, usuario_id)
            )
            mensajes = await cursor.fetchall()

        return [
            {
                "id": m[0],
                "emisor_id": m[1],
                "receptor_id": m[2],
                "contenido": m[3],
                "timestamp": m[4].isoformat()
            }
            for m in mensajes
        ]

    finally:
        await release_connection(conn)