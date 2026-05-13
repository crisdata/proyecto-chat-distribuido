# worker.py
# Proceso independiente que consume eventos de la cola RabbitMQ.
# Se ejecuta en su propio contenedor Docker (chat_worker).
#
# Responsabilidades:
#   1. Consumir eventos de la cola "mensajes"
#   2. Llamar al endpoint interno de la API para notificar via WebSocket
#   3. Reintentar bajo fallos transitorios y descartar tras 3 intentos
#   4. Mantener la trazabilidad mediante request_id que llega en el
#      payload del mensaje y se propaga al header HTTP de la llamada
#      interna a la API.

import asyncio
import json
import logging
import os
import sys

import aio_pika
import aiohttp
from dotenv import load_dotenv

from app.request_id import set_request_id, get_request_id
from app.logging_config import configurar_logging

load_dotenv()

# ── Configuración ──────────────────────────────────────────────────────────

RABBITMQ_URL = (
    f"amqp://{os.getenv('RABBITMQ_USER', 'guest')}:"
    f"{os.getenv('RABBITMQ_PASSWORD', 'guest')}@"
    f"{os.getenv('RABBITMQ_HOST', 'rabbitmq')}:"
    f"{os.getenv('RABBITMQ_PORT', '5672')}/"
)

API_INTERNA_URL = os.getenv('API_INTERNA_URL', 'http://api:8000')

WORKER_SECRET = os.getenv('WORKER_SECRET')
if not WORKER_SECRET:
    raise RuntimeError(
        "WORKER_SECRET no está definido en las variables de entorno. "
        "El worker no puede autenticarse contra la API sin él."
    )

PREFETCH = 5
MAX_REINTENTOS = 3
TIMEOUT_HTTP_SEGUNDOS = 10

# ── Logging ────────────────────────────────────────────────────────────────
# Reutilizamos la misma configuración de logging que la API para mantener
# el formato consistente con request_id automático.
configurar_logging()
log = logging.getLogger("worker")


# ── Procesamiento de mensajes ──────────────────────────────────────────────

async def llamar_api_notificar(
    session: aiohttp.ClientSession,
    receptor_id: str,
    emisor_id: str,
    emisor_nombre: str,
) -> tuple[bool, bool]:
    """
    Llama al endpoint interno de la API.
    Propaga el request_id actual via header X-Request-ID para que la
    API continúe la cadena de trazabilidad en sus propios logs.
    Retorna (exito, recuperable).
    """
    try:
        async with session.post(
            f"{API_INTERNA_URL}/interno/notificar",
            json={
                "receptor_id": receptor_id,
                "emisor_id": emisor_id,
                "emisor_nombre": emisor_nombre,
            },
            headers={
                "X-Worker-Secret": WORKER_SECRET,
                "X-Request-ID": get_request_id(),
            },
            timeout=aiohttp.ClientTimeout(total=TIMEOUT_HTTP_SEGUNDOS),
        ) as respuesta:
            if respuesta.status == 200:
                return True, False
            if respuesta.status == 403:
                log.error(
                    "Autenticación rechazada por la API. "
                    "Verifica que WORKER_SECRET coincida en api y worker."
                )
                return False, False
            if respuesta.status >= 500:
                log.warning(
                    f"API respondió {respuesta.status}, reintento programado"
                )
                return False, True
            log.error(
                f"API respondió {respuesta.status} (error de datos), "
                f"el mensaje será descartado"
            )
            return False, False
    except asyncio.TimeoutError:
        log.warning("Timeout llamando a la API, reintento programado")
        return False, True
    except aiohttp.ClientError as e:
        log.warning(f"Error de red llamando a la API ({e}), reintento programado")
        return False, True


async def procesar_mensaje(
    message: aio_pika.IncomingMessage,
    session: aiohttp.ClientSession,
):
    """
    Procesa un evento de mensaje recibido de la cola.
    Lo primero que hace es adoptar el request_id del evento en su
    propio ContextVar, para que todos los logs de este procesamiento
    lleven automáticamente el ID original que generó la API.
    """
    try:
        evento = json.loads(message.body.decode())
    except json.JSONDecodeError:
        log.error(f"Evento con JSON inválido, descartado: {message.body!r}")
        await message.ack()
        return

    # Adoptar el request_id del evento para que los logs del worker
    # mantengan la cadena de trazabilidad iniciada en la API.
    # Si el evento no trae request_id (mensaje antiguo o malformado),
    # usamos "-" como marcador de "sin trazabilidad".
    request_id = evento.get("request_id", "-")
    set_request_id(request_id)

    receptor_id = evento.get("receptor_id")
    emisor_id = evento.get("emisor_id")
    emisor_nombre = evento.get("emisor_nombre")

    if not all([receptor_id, emisor_id, emisor_nombre]):
        log.error(f"Evento malformado, descartado: {evento}")
        await message.ack()
        return

    log.info(f"Evento recibido de {emisor_nombre} para {receptor_id}")

    headers = message.headers or {}
    intento = int(headers.get("x-reintentos", 0))

    exito, recuperable = await llamar_api_notificar(
        session, receptor_id, emisor_id, emisor_nombre
    )

    if exito:
        log.info(f"Notificado: {emisor_nombre} → {receptor_id}")
        await message.ack()
        return

    if not recuperable:
        await message.ack()
        return

    if intento + 1 >= MAX_REINTENTOS:
        log.error(
            f"Mensaje descartado tras {MAX_REINTENTOS} reintentos: "
            f"{emisor_nombre} → {receptor_id}"
        )
        await message.ack()
        return

    await republicar_con_reintento(message, evento, intento + 1)
    log.warning(
        f"Reintento {intento + 1}/{MAX_REINTENTOS} programado: "
        f"{emisor_nombre} → {receptor_id}"
    )
    await message.ack()


async def republicar_con_reintento(
    message: aio_pika.IncomingMessage,
    evento: dict,
    nuevo_intento: int,
):
    """
    Republica el mensaje en la misma cola con el contador de reintentos
    actualizado. El request_id permanece en el body del evento para
    mantener la trazabilidad a través de los reintentos.
    """
    canal = message.channel
    nuevo_mensaje = aio_pika.Message(
        body=json.dumps(evento).encode(),
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        headers={"x-reintentos": nuevo_intento},
    )
    await asyncio.sleep(2 * nuevo_intento)
    await canal.default_exchange.publish(
        nuevo_mensaje,
        routing_key="mensajes",
    )


# ── Punto de entrada ───────────────────────────────────────────────────────

async def main():
    """
    Conecta a RabbitMQ, crea la sesión HTTP global y queda
    consumiendo la cola hasta que se reciba una señal de apagado.
    """
    log.info("Iniciando worker")

    conexion = await aio_pika.connect_robust(RABBITMQ_URL)
    canal = await conexion.channel()
    await canal.set_qos(prefetch_count=PREFETCH)
    cola = await canal.declare_queue("mensajes", durable=True)

    session = aiohttp.ClientSession()

    log.info(f"Escuchando cola 'mensajes' (prefetch={PREFETCH})")

    try:
        async def callback(message: aio_pika.IncomingMessage):
            await procesar_mensaje(message, session)

        await cola.consume(callback)
        await asyncio.Future()
    finally:
        log.info("Cerrando worker")
        await session.close()
        await conexion.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Worker detenido manualmente")