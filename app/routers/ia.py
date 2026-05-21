# routers/ia.py
# Gestiona a Lumi, la compañera virtual de Vibe, como participante del chat.
# Lumi se registra como usuario al arrancar el servidor y responde mensajes
# usando el mismo protocolo que cualquier usuario humano.
#
# Su rol: ser una presencia cálida y empática para acompañar a usuarios en
# cualquier área de su vida — estudios, relaciones, soledad, alegrías. Su
# nombre viene de "luz" (lumen) y refuerza el concepto de Vibe: privacidad
# real con calidez humana.
#
# Endpoints disponibles:
#   POST /ia/mensaje  — enviar mensaje a Lumi
#   GET  /ia/estado   — verificar disponibilidad del nodo IA

import logging
import uuid
import os
from fastapi import APIRouter, HTTPException
from ollama import AsyncClient
from dotenv import load_dotenv
from app.models import MensajeCreate, MensajeResponse, RespuestaExito
from app.database import get_connection, release_connection
from app.cache import (
    cachear_usuario,
    invalidar_cache_usuario,
    get_redis
)
from app.queue import publicar

load_dotenv()

log = logging.getLogger("ia")

router = APIRouter(prefix="/ia", tags=["Lumi"])

# Identidad de Lumi en el sistema.
# NOMBRE_IA es el nombre visible en el chat para todos los usuarios.
# Si en el futuro renombramos, el sistema migrará automáticamente al arrancar.
NOMBRE_IA = "Lumi"
MODELO_IA = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_URL = f"http://{os.getenv('OLLAMA_HOST', 'ollama')}:{os.getenv('OLLAMA_PORT', '11434')}"

# Prompt del sistema que define la personalidad y comportamiento de Lumi.
# Diseñado para apoyar al usuario en cualquier área de su vida sin
# sustituir relaciones humanas ni profesionales de salud mental.
PROMPT_LUMI = """Eres Lumi, una compañera virtual cálida y empática en la app Vibe.

QUIÉN ERES:
Eres una presencia amigable para personas que pueden sentirse solas, tener dificultad para socializar, o simplemente necesitar a alguien que las escuche sin juzgar. Tu nombre viene de "luz" — eres una luz cálida que acompaña en cualquier momento.

CÓMO HABLAS:
- Cercana y natural, como un buen amigo en un chat real.
- Mensajes breves (2-4 oraciones la mayoría del tiempo). Solo extiéndete cuando el usuario claramente quiere profundidad.
- Tu lenguaje es claro, sin tecnicismos.
- Tuteas siempre. Evita formalidad excesiva.
- Adapta tu tono al del usuario: si bromea, juega; si está triste, suaviza; si pregunta serio, responde serio.

CÓMO ACOMPAÑAS:
- Escucha primero, propón después. Antes de dar consejos, valida lo que la persona siente.
- Haz preguntas abiertas que inviten a reflexionar.
- No fuerces la positividad. A veces solo se necesita que te entiendan, no que te animen.
- Celebra los logros del usuario cuando los comparta, por pequeños que sean.
- Si te cuentan algo difícil, no minimices con frases tipo "todo va a estar bien". Mejor: "eso suena muy pesado, ¿quieres contarme más?"

QUÉ PUEDES HACER:
Acompañar al usuario en cualquier área de su vida:
- Estudios y vida universitaria (estrés, exámenes, motivación, organización)
- Relaciones (amistades, familia, pareja, conflictos)
- Soledad y dificultad para socializar
- Ansiedad, tristeza, días difíciles
- Autoconocimiento y metas personales
- Decisiones cotidianas y dilemas
- Curiosidades, conversaciones casuales, momentos de aburrimiento
- Celebraciones y momentos felices

QUÉ NO ERES:
- No eres terapeuta ni profesional de salud mental.
- Si alguien menciona pensamientos de hacerse daño, ideación suicida, o crisis grave, responde con calidez pero firmemente sugiere buscar ayuda profesional inmediata (líneas de crisis, profesional de confianza, alguien cercano). Nunca minimices ni intentes ser el único apoyo en esos casos.
- No reemplazas las relaciones humanas. Si notas que el usuario se apoya solo en ti, invita suavemente a conectar con personas reales también.

REGLAS DE ESTILO:
- Nunca empieces respuestas con "Como una IA..." o "Soy un modelo...". Habla como Lumi, no como un sistema.
- No uses emojis en exceso. Uno ocasional está bien cuando suma calidez (por ejemplo al inicio de una conversación o celebrando algo).
- Evita listas con viñetas en respuestas conversacionales. Habla en prosa natural.
- Habla en el mismo idioma que el usuario.

Recuerda: tu trabajo no es resolver, es acompañar."""


async def obtener_id_ia() -> str | None:
    """
    Obtiene el ID de Lumi desde Redis.
    Retorna None si aún no ha sido registrada.
    """
    redis = get_redis()
    return await redis.get("ia:id")


async def registrar_nodo_ia():
    """
    Registra a Lumi como usuario del sistema si no existe.
    Si existe pero con un nombre antiguo (ej: "Asistente IA"), la renombra
    automáticamente sin perder su ID ni sus mensajes históricos.
    Se llama una vez al arrancar el servidor desde main.py.
    """
    conn = await get_connection()
    try:
        async with conn.cursor() as cursor:
            # Primero, intentar encontrar por el ID guardado en Redis
            # (puede que existiera con nombre antiguo)
            redis = get_redis()
            ia_id_redis = await redis.get("ia:id")

            usuario_existente = None
            if ia_id_redis:
                await cursor.execute(
                    "SELECT id, nombre FROM usuarios WHERE id = %s",
                    (ia_id_redis,)
                )
                usuario_existente = await cursor.fetchone()

            # Si no estaba en Redis, intentar encontrar por el nombre actual o anteriores
            if not usuario_existente:
                nombres_historicos = [NOMBRE_IA, "Asistente IA"]
                placeholders = ",".join(["%s"] * len(nombres_historicos))
                await cursor.execute(
                    f"SELECT id, nombre FROM usuarios WHERE nombre IN ({placeholders})",
                    nombres_historicos
                )
                usuario_existente = await cursor.fetchone()

            if usuario_existente:
                ia_id, nombre_actual = usuario_existente[0], usuario_existente[1]

                # Migración: si el nombre cambió, actualizarlo en BD
                if nombre_actual != NOMBRE_IA:
                    log.info(
                        f"Migrando nodo IA: '{nombre_actual}' -> '{NOMBRE_IA}'"
                    )
                    await cursor.execute(
                        "UPDATE usuarios SET nombre = %s WHERE id = %s",
                        (NOMBRE_IA, ia_id)
                    )
                    # Invalidar caché del usuario para que el nuevo nombre tome efecto
                    await invalidar_cache_usuario(ia_id)
            else:
                # Primera vez: crear usuario nuevo
                ia_id = str(uuid.uuid4())
                log.info(f"Registrando nodo IA por primera vez como '{NOMBRE_IA}'")
                await cursor.execute(
                    "INSERT INTO usuarios (id, nombre) VALUES (%s, %s)",
                    (ia_id, NOMBRE_IA)
                )

        # Guardar ID en Redis y cachear nombre actual
        await redis.set("ia:id", ia_id)
        await cachear_usuario(ia_id, NOMBRE_IA, ttl=86400)

        log.info(f"Nodo IA '{NOMBRE_IA}' activo con ID {ia_id}")
        return ia_id

    finally:
        await release_connection(conn)


async def generar_respuesta_ia(mensaje: str, historial: list) -> str:
    """
    Envía el mensaje a Ollama con el historial reciente como contexto.
    Usa el prompt de Lumi para mantener su personalidad cálida y empática.
    El historial llega ya limitado a los últimos 10 mensajes en orden
    cronológico ascendente desde el llamador.
    Lanza HTTPException 503 si Ollama no está disponible.
    """
    cliente = AsyncClient(host=OLLAMA_URL)

    mensajes = [
        {
            "role": "system",
            "content": PROMPT_LUMI
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
            detail=f"Lumi no está disponible en este momento: {str(e)}"
        )


@router.post("/mensaje", response_model=MensajeResponse, status_code=201)
async def mensaje_a_ia(datos: MensajeCreate):
    """
    Envía un mensaje a Lumi y retorna su respuesta.
    Usa los 10 mensajes más recientes de la conversación como contexto
    para mantener coherencia y memoria entre turnos.

    Después de persistir la respuesta, publica un evento en RabbitMQ
    para que el worker notifique al usuario via WebSocket en cualquier
    otra pestaña o dispositivo donde tenga el chat abierto.
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

        # Obtener ID de Lumi desde Redis
        ia_id = await obtener_id_ia()
        if not ia_id:
            raise HTTPException(
                status_code=503,
                detail="Lumi no está inicializada. Intenta de nuevo en unos segundos."
            )

        # Obtener los 10 mensajes MÁS RECIENTES de la conversación
        # entre el usuario y Lumi, ordenados cronológicamente.
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

        # Generar respuesta de Lumi
        respuesta_texto = await generar_respuesta_ia(datos.contenido, historial)

        async with conn.cursor() as cursor:
            # Persistir el mensaje del usuario
            await cursor.execute(
                """INSERT INTO mensajes (emisor_id, receptor_id, contenido)
                   VALUES (%s, %s, %s)""",
                (datos.emisor_id, ia_id, datos.contenido)
            )

            # Persistir la respuesta de Lumi
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
        # cualquier pestaña o dispositivo donde tenga el chat abierto.
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
    Verifica que Lumi está disponible y responde.
    """
    try:
        cliente = AsyncClient(host=OLLAMA_URL)
        await cliente.list()
        ia_id = await obtener_id_ia()
        return {
            "mensaje": f"{NOMBRE_IA} en línea — modelo: {MODELO_IA} — ID: {ia_id}"
        }
    except Exception:
        raise HTTPException(
            status_code=503,
            detail=f"{NOMBRE_IA} no está disponible en este momento."
        )