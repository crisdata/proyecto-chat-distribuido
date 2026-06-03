# routers/ia.py
# Gestiona a Lumi, la compañera virtual de Vibe, como participante del chat.
# Lumi se registra como usuario al arrancar el servidor y responde mensajes
# usando el mismo protocolo que cualquier usuario humano.
#
# RESILIENCIA: si Ollama no está disponible, Lumi responde con uno de varios
# mensajes empáticos preconfigurados en su voz, en lugar de devolver un error
# técnico. Esto preserva la sensación de "compañera siempre presente" incluso
# cuando el motor de IA está caído.
#
# Endpoints disponibles:
#   POST /ia/mensaje  — enviar mensaje a Lumi
#   GET  /ia/estado   — verificar disponibilidad del nodo IA

import logging
import os
from datetime import datetime, timezone
import random
import uuid
import os

from fastapi import APIRouter, Depends, HTTPException
from ollama import AsyncClient
from dotenv import load_dotenv

from app.models import MensajeCreate, MensajeResponse, RespuestaExito, IAModoRequest
from app.database import get_connection, release_connection
from app.cache import (
    cachear_usuario,
    invalidar_cache_usuario,
    get_redis
)
from app.queue import publicar
from app.auth import autenticar_usuario_actual

load_dotenv()

log = logging.getLogger("ia")

router = APIRouter(prefix="/ia", tags=["Lumi"])

# Identidad de Lumi en el sistema.
NOMBRE_IA = "Lumi"
MODELO_IA = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_URL = f"http://{os.getenv('OLLAMA_HOST', 'ollama')}:{os.getenv('OLLAMA_PORT', '11434')}"

# Timeout generoso para llamadas a Ollama. La primera respuesta tras
# un reinicio puede tardar 30-60s porque el modelo necesita cargar en RAM.
# Para respuestas subsiguientes el modelo ya está "caliente" y responde
# en pocos segundos. 120s da margen suficiente para ambos casos.
TIMEOUT_OLLAMA_SEGUNDOS = 120

# Mensajes de fallback que Lumi responde cuando Ollama no está disponible.
# Escritos en su propia voz (cálida, breve, empática) para que el usuario
# perciba continuidad en la personalidad incluso ante fallos del motor de IA.
MENSAJES_FALLBACK = [
    "Disculpa, ahora mismo estoy descansando y no puedo responderte con toda mi atención. Vuelve en un momento y conversamos con calma.",
    "Mi mente está procesando muchas cosas en este instante. ¿Podríamos hablar en unos minutos? Aquí estaré esperándote.",
    "Estoy en silencio un rato, recargando energías. Mientras tanto, ¿qué te parece escribir lo que sientes? A veces solo poner las cosas en palabras ya ayuda.",
    "Tengo dificultad para responderte ahora mismo. No es por ti, son cosas mías. ¿Puedes intentar de nuevo en un momento?",
    "Pausa breve por mi parte. Si quieres, deja tu mensaje y cuando vuelva con energía te respondo con toda mi atención.",
]

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


# ── Health check de Ollama ───────────────────────────────────────────────────

async def verificar_ollama_disponible() -> bool:
    """
    Verifica si Ollama está respondiendo. Usado por dos cosas:
    1. Decidir si usar fallback empático en lugar de llamada real
    2. Reportar el estado de presencia de Lumi al frontend

    Implementación liviana: llama a la API de Ollama con un timeout corto.
    Si responde, está disponible. Si falla por cualquier razón, no lo está.
    """
    try:
        cliente = AsyncClient(host=OLLAMA_URL, timeout=10)
        await cliente.list()
        return True
    except Exception:
        return False


def obtener_mensaje_fallback() -> str:
    """
    Retorna un mensaje de fallback aleatorio en la voz de Lumi.
    La aleatoriedad evita que el usuario reciba siempre el mismo mensaje
    si Ollama está caído por un período prolongado.
    """
    return random.choice(MENSAJES_FALLBACK)


async def precalentar_modelo():
    """
    Pre-carga el modelo en RAM enviando una petición trivial al arrancar.
    Esto evita que el primer usuario en mandar un mensaje sufra el delay
    de 30-60s necesario para cargar el modelo en memoria por primera vez.
    Si falla, no es crítico: simplemente el primer usuario tendrá fallback.
    """
    try:
        cliente = AsyncClient(host=OLLAMA_URL, timeout=TIMEOUT_OLLAMA_SEGUNDOS)
        log.info(f"Pre-calentando modelo {MODELO_IA}...")
        await cliente.chat(
            model=MODELO_IA,
            messages=[{"role": "user", "content": "Hi"}]
        )
        log.info(f"Modelo {MODELO_IA} listo para responder rápidamente")
    except Exception as e:
        log.warning(
            f"No se pudo pre-calentar el modelo: {type(e).__name__}: {e}. "
            "El primer mensaje del usuario puede usar fallback."
        )


# ── Identidad de Lumi ────────────────────────────────────────────────────────

async def obtener_id_ia() -> str | None:
    """Obtiene el ID de Lumi desde Redis."""
    redis = get_redis()
    return await redis.get("ia:id")


async def registrar_nodo_ia():
    """
    Registra a Lumi como usuario del sistema si no existe.
    Si existe pero con un nombre antiguo (ej: "Asistente IA"), la renombra
    automáticamente sin perder su ID ni sus mensajes históricos.
    """
    conn = await get_connection()
    try:
        async with conn.cursor() as cursor:
            redis = get_redis()
            ia_id_redis = await redis.get("ia:id")

            usuario_existente = None
            if ia_id_redis:
                await cursor.execute(
                    "SELECT id, nombre FROM usuarios WHERE id = %s",
                    (ia_id_redis,)
                )
                usuario_existente = await cursor.fetchone()

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

                if nombre_actual != NOMBRE_IA:
                    log.info(
                        f"Migrando nodo IA: '{nombre_actual}' -> '{NOMBRE_IA}'"
                    )
                    await cursor.execute(
                        "UPDATE usuarios SET nombre = %s WHERE id = %s",
                        (NOMBRE_IA, ia_id)
                    )
                    await invalidar_cache_usuario(ia_id)
            else:
                ia_id = str(uuid.uuid4())
                log.info(f"Registrando nodo IA por primera vez como '{NOMBRE_IA}'")
                await cursor.execute(
                    "INSERT INTO usuarios (id, nombre) VALUES (%s, %s)",
                    (ia_id, NOMBRE_IA)
                )

        await redis.set("ia:id", ia_id)
        await cachear_usuario(ia_id, NOMBRE_IA, ttl=86400)

        log.info(f"Nodo IA '{NOMBRE_IA}' activo con ID {ia_id}")

        # El pre-calentamiento del modelo se hace en background desde main.py
        # para no bloquear el arranque de la API.

        return ia_id

    finally:
        await release_connection(conn)


# ── Generación de respuestas ─────────────────────────────────────────────────

async def generar_respuesta_ia(mensaje: str, historial: list) -> tuple[str, bool]:
    """
    Envía el mensaje a Ollama con el historial reciente como contexto.
    Retorna una tupla (respuesta, exito_real).

    Si Ollama responde correctamente, retorna (respuesta_real, True).
    Si Ollama falla (timeout, error, no disponible), retorna (mensaje_fallback, False).
    Esto evita lanzar excepciones HTTP y permite que la conversación continúe
    incluso si el motor de IA está caído.
    """
    cliente = AsyncClient(host=OLLAMA_URL, timeout=TIMEOUT_OLLAMA_SEGUNDOS)

    mensajes = [{"role": "system", "content": PROMPT_LUMI}]

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
        return respuesta.message.content, True
    except Exception as e:
        log.warning(
            f"Ollama no respondió, usando mensaje fallback. Causa: {type(e).__name__}: {e}"
        )
        return obtener_mensaje_fallback(), False


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/mensaje", response_model=MensajeResponse, status_code=201)
async def mensaje_a_ia(
    datos: MensajeCreate,
    payload: dict = Depends(autenticar_usuario_actual)
):
    """
    Envía un mensaje a Lumi y retorna su respuesta.
    Si Ollama está disponible, devuelve respuesta generada por el modelo.
    Si Ollama está caído, devuelve un mensaje fallback empático en la voz
    de Lumi, manteniendo la continuidad de la conversación.
    """
    if datos.emisor_id != payload["sub"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    conn = await get_connection()
    try:
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

        ia_id = await obtener_id_ia()
        if not ia_id:
            raise HTTPException(
                status_code=503,
                detail="Lumi no está inicializada. Intenta de nuevo en unos segundos."
            )

        async with conn.cursor() as cursor:
            await cursor.execute(
                """SELECT emisor_id, contenido FROM (
                       SELECT emisor_id, contenido, timestamp
                       FROM mensajes
                       WHERE ((emisor_id = %s AND receptor_id = %s)
                          OR (emisor_id = %s AND receptor_id = %s))
                         AND (expira_en IS NULL OR expira_en > NOW())
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

        # Generar respuesta (real o fallback según disponibilidad de Ollama)
        respuesta_texto, _ = await generar_respuesta_ia(datos.contenido, historial)

        async with conn.cursor() as cursor:
            await cursor.execute(
                """INSERT INTO mensajes (emisor_id, receptor_id, contenido)
                   VALUES (%s, %s, %s)""",
                (datos.emisor_id, ia_id, datos.contenido)
            )

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
    disponible = await verificar_ollama_disponible()
    if disponible:
        ia_id = await obtener_id_ia()
        return {
            "mensaje": f"{NOMBRE_IA} en línea — modelo: {MODELO_IA} — ID: {ia_id}"
        }
    else:
        raise HTTPException(
            status_code=503,
            detail=f"{NOMBRE_IA} está descansando — el motor de IA no responde."
        )


# ── Contexto RAM para modo sin memoria ────────────────────────────────────

_lumi_contextos: dict[str, list[dict]] = {}  # key: usuario_id
_LUMI_WINDOW = 10  # últimos N mensajes de la sesión


@router.post("/mensaje/modo", response_model=MensajeResponse, status_code=201)
async def mensaje_a_ia_con_modo(
    datos: IAModoRequest,
    payload: dict = Depends(autenticar_usuario_actual),
):
    """
    Envía un mensaje a Lumi con selector de modo.

    - con_memoria: usa historial persistido y guarda todo en DB.
    - sin_memoria: usa contexto RAM por sesión sin persistir nada.
    """
    if datos.emisor_id != payload["sub"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    ia_id = await obtener_id_ia()
    if not ia_id:
        raise HTTPException(
            status_code=503,
            detail="Lumi no está inicializada.",
        )

    if datos.modo == "sin_memoria":
        return await _responder_sin_memoria(datos, ia_id, payload["sub"])

    # con_memoria: delegar al flujo existente
    return await mensaje_a_ia(
        MensajeCreate(
            emisor_id=datos.emisor_id,
            receptor_id=datos.receptor_id,
            contenido=datos.contenido,
        ),
        payload,
    )


async def _responder_sin_memoria(
    datos: IAModoRequest, ia_id: str, usuario_id: str
) -> MensajeResponse:
    """Genera respuesta sin memoria: contexto RAM, sin DB."""
    ctx = _lumi_contextos.setdefault(usuario_id, [])

    # Construir contexto desde RAM
    historial = []
    for entry in ctx:
        historial.append({
            "es_usuario": entry["es_usuario"],
            "contenido": entry["contenido"],
        })

    respuesta_texto, _ = await generar_respuesta_ia(datos.contenido, historial)

    # Actualizar RAM (rolling window)
    ctx.append({"es_usuario": True, "contenido": datos.contenido})
    ctx.append({"es_usuario": False, "contenido": respuesta_texto})
    if len(ctx) > _LUMI_WINDOW:
        _lumi_contextos[usuario_id] = ctx[-_LUMI_WINDOW:]

    return {
        "id": None,  # pyright: ignore[reportReturnType]
        "emisor_id": ia_id,
        "receptor_id": usuario_id,
        "contenido": respuesta_texto,
        "timestamp": datetime.now(timezone.utc),
        "expira_en": None,
    }