# worker.py
# Proceso independiente que consume eventos de la cola RabbitMQ.
# Se ejecuta en su propio contenedor Docker (chat_worker).
#
# Responsabilidades:
#   1. Consumir eventos de la cola "mensajes"
#   2. Llamar al endpoint interno de la API para notificar via WebSocket
#   3. Reintentar bajo fallos transitorios y descartar tras 3 intentos
#
# Diseño:
#   - Una sola aiohttp.ClientSession compartida (creada en main).
#   - Prefetch de 5 mensajes para concurrencia controlada.
#   - Reintentos: el mensaje vuelve a la cola si la API falla con 5xx
#     o hay error de red. Después de MAX_REINTENTOS, se descarta.
#   - Logging estructurado con niveles INFO, WARNING y ERROR.

import asyncio
import json
import logging
import os
import sys

import aio_pika
import aiohttp
from dotenv import load_dotenv

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

# Cuántos mensajes procesa el worker en paralelo.
# Un valor bajo evita saturar la API; uno alto aprovecha asyncio.
PREFETCH = 5

# Cuántas veces reintentamos un mensaje antes de descartarlo.
# El conteo se lleva en el header 'x-reintentos' del mensaje.
MAX_REINTENTOS = 3

# Tiempo de espera HTTP por llamada a la API interna.
TIMEOUT_HTTP_SEGUNDOS = 10

# ── Logging ────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [worker] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout,
)
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
    Retorna (exito, recuperable):
      - exito=True si la API respondió 200 OK
      - recuperable=True si el fallo es transitorio (5xx, red caída)
        y el mensaje merece reintento. False para errores definitivos
        (403, 422, etc.) que no van a mejorar reintentando.
    """
    try:
        async with session.post(
            f"{API_INTERNA_URL}/interno/notificar",
            json={
                "receptor_id": receptor_id,
                "emisor_id": emisor_id,
                "emisor_nombre": emisor_nombre,
            },
            headers={"X-Worker-Secret": WORKER_SECRET},
            timeout=aiohttp.ClientTimeout(total=TIMEOUT_HTTP_SEGUNDOS),
        ) as respuesta:
            if respuesta.status == 200:
                return True, False
            if respuesta.status == 403:
                log.error(
                    "Autenticación rechazada por la API. "
                    "Verifica que WORKER_SECRET coincida en api y worker."
                )
                return False, False  # no recuperable
            if respuesta.status >= 500:
                log.warning(
                    f"API respondió {respuesta.status}, reintento programado"
                )
                return False, True  # recuperable
            # 4xx no autorizados arriba (400, 422) — error de datos
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
    Estrategia de manejo de errores:
      - Si la API responde OK → ack (mensaje confirmado).
      - Si el error es no recuperable → ack (descartado, no tiene sentido reintentar).
      - Si el error es recuperable y aún hay reintentos disponibles →
        publicar copia con contador incrementado y ack del original.
      - Si el error es recuperable pero ya agotamos reintentos → ack y log de error.
    """
    try:
        evento = json.loads(message.body.decode())
    except json.JSONDecodeError:
        log.error(f"Evento con JSON inválido, descartado: {message.body!r}")
        await message.ack()
        return

    receptor_id = evento.get("receptor_id")
    emisor_id = evento.get("emisor_id")
    emisor_nombre = evento.get("emisor_nombre")

    if not all([receptor_id, emisor_id, emisor_nombre]):
        log.error(f"Evento malformado, descartado: {evento}")
        await message.ack()
        return

    # Conteo de reintentos llevado en headers del mensaje
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
        # Error definitivo, no tiene sentido reintentar
        await message.ack()
        return

    # Error recuperable: ¿queda presupuesto de reintentos?
    if intento + 1 >= MAX_REINTENTOS:
        log.error(
            f"Mensaje descartado tras {MAX_REINTENTOS} reintentos: "
            f"{emisor_nombre} → {receptor_id}"
        )
        await message.ack()
        return

    # Republicamos el mensaje con el contador incrementado
    await republicar_con_reintento(
        message,
        evento,
        intento + 1,
    )
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
    Publica una copia del mensaje en la misma cola con el contador
    de reintentos actualizado. Usa el canal del mensaje original
    para no abrir conexiones nuevas.
    """
    canal = message.channel
    nuevo_mensaje = aio_pika.Message(
        body=json.dumps(evento).encode(),
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        headers={"x-reintentos": nuevo_intento},
    )
    # Pequeña pausa antes de republicar para no saturar la API
    # cuando está caída — backoff lineal simple.
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

    # Conexión robusta — aio-pika reconecta automáticamente si RabbitMQ cae.
    conexion = await aio_pika.connect_robust(RABBITMQ_URL)
    canal = await conexion.channel()
    await canal.set_qos(prefetch_count=PREFETCH)
    cola = await canal.declare_queue("mensajes", durable=True)

    # Sesión HTTP única y reutilizable durante toda la vida del worker
    session = aiohttp.ClientSession()

    log.info(f"Escuchando cola 'mensajes' (prefetch={PREFETCH})")

    try:
        # callback que captura la session por closure
        async def callback(message: aio_pika.IncomingMessage):
            await procesar_mensaje(message, session)

        await cola.consume(callback)

        # Mantener el worker corriendo indefinidamente
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