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

load_dotenv()

router = APIRouter(prefix="/ia", tags=["Inteligencia Artificial"])

# Nombre del nodo IA visible en el chat para todos los usuarios
NOMBRE_IA = "Asistente IA"
MODELO_IA = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_URL = f"http://{os.getenv('OLLAMA_HOST', 'ollama')}:{os.getenv('OLLAMA_PORT', '11434')}"

# Nota Corte 3: el AsyncClient se crea en cada llamada.
# En el Corte 3 se reemplaza por un cliente único reutilizable
# para reducir overhead de conexión bajo carga alta.


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
    El nodo IA usa el mismo modelo de datos que cualquier usuario humano,
    lo que demuestra que la arquitectura soporta cualquier tipo de nodo
    sin modificaciones al sistema base.
    """
    conn = await get_connection()
    try:
        async with conn.cursor() as cursor:

            # Verificar si el nodo IA ya está registrado en MariaDB
            await cursor.execute(
                "SELECT id FROM usuarios WHERE nombre = %s",
                (NOMBRE_IA,)
            )
            existente = await cursor.fetchone()

            if existente:
                # Ya existe, recuperar su ID
                ia_id = existente[0]
            else:
                # Primera vez que arranca el sistema, registrar el nodo IA
                ia_id = str(uuid.uuid4())
                await cursor.execute(
                    "INSERT INTO usuarios (id, nombre) VALUES (%s, %s)",
                    (ia_id, NOMBRE_IA)
                )

        # Guardar ID en Redis con TTL de 24 horas para acceso rápido
        redis = get_redis()
        await redis.set("ia:id", ia_id)
        await cachear_usuario(ia_id, NOMBRE_IA, ttl=86400)

        return ia_id

    finally:
        await release_connection(conn)


async def generar_respuesta_ia(mensaje: str, historial: list) -> str:
    """
    Envía el mensaje a Ollama con el historial reciente como contexto.
    El historial permite que la IA recuerde lo que se habló antes
    en la misma conversación, dando coherencia a las respuestas.
    Lanza HTTPException 503 si Ollama no está disponible.
    """
    cliente = AsyncClient(host=OLLAMA_URL)

    # Sistema: define el comportamiento del nodo IA dentro del chat
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

    # Incluir los últimos 10 mensajes del historial como contexto
    for h in historial[-10:]:
        mensajes.append({
            "role": "user" if h["es_usuario"] else "assistant",
            "content": h["contenido"]
        })

    # Agregar el mensaje actual del usuario
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
    El nodo IA responde usando el historial de la conversación
    para mantener contexto entre mensajes.
    Tanto el mensaje del usuario como la respuesta de la IA
    se persisten en MariaDB como mensajes normales del sistema.
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

        # Obtener historial de la conversación entre el usuario y la IA
        async with conn.cursor() as cursor:
            await cursor.execute(
                """SELECT emisor_id, contenido FROM mensajes
                   WHERE (emisor_id = %s AND receptor_id = %s)
                      OR (emisor_id = %s AND receptor_id = %s)
                   ORDER BY timestamp ASC
                   LIMIT 10""",
                (datos.emisor_id, ia_id, ia_id, datos.emisor_id)
            )
            historial_raw = await cursor.fetchall()

        # Construir historial en formato que entiende generar_respuesta_ia
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

            # Persistir la respuesta de la IA como mensaje del nodo IA
            await cursor.execute(
                """INSERT INTO mensajes (emisor_id, receptor_id, contenido)
                   VALUES (%s, %s, %s)""",
                (ia_id, datos.emisor_id, respuesta_texto)
            )
            respuesta_id = cursor.lastrowid

            # Obtener el mensaje completo con su timestamp generado por MariaDB
            await cursor.execute(
                """SELECT id, emisor_id, receptor_id, contenido, timestamp
                   FROM mensajes WHERE id = %s""",
                (respuesta_id,)
            )
            respuesta = await cursor.fetchone()

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
    El frontend usa este endpoint para mostrar si la IA está en línea.
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