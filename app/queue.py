# queue.py
# Gestiona la conexión a RabbitMQ y la publicación de eventos.
# Usa aio-pika para compatibilidad total con asyncio y FastAPI.
#
# Cada evento publicado incluye automáticamente el request_id de la
# petición HTTP en curso, permitiendo trazar el flujo del mensaje a
# través de la cola hasta el worker.

import logging
import os
import json

import aio_pika
from dotenv import load_dotenv

from app.request_id import get_request_id

load_dotenv()

log = logging.getLogger("queue")

# Conexión y canal compartidos por toda la aplicación
_conexion = None
_canal = None


async def conectar_queue():
    """
    Crea la conexión a RabbitMQ al iniciar la aplicación.
    Se llama desde el lifespan de main.py.
    """
    global _conexion, _canal

    url = (
        f"amqp://{os.getenv('RABBITMQ_USER', 'guest')}:"
        f"{os.getenv('RABBITMQ_PASSWORD', 'guest')}@"
        f"{os.getenv('RABBITMQ_HOST', 'rabbitmq')}:"
        f"{os.getenv('RABBITMQ_PORT', '5672')}/"
    )

    _conexion = await aio_pika.connect_robust(url)
    _canal = await _conexion.channel()

    await _canal.declare_queue("mensajes", durable=True)
    log.info("Cola 'mensajes' declarada en RabbitMQ")


async def desconectar_queue():
    """Cierra la conexión a RabbitMQ al apagar la aplicación."""
    global _conexion
    if _conexion:
        await _conexion.close()
        log.info("Conexión RabbitMQ cerrada")


async def publicar(cola: str, evento: dict):
    """
    Publica un evento JSON en la cola especificada.
    Inyecta automáticamente el request_id del contexto HTTP actual
    para que el worker pueda continuar la cadena de trazabilidad.

    Si la conexión no está disponible, el error se registra
    pero no interrumpe el flujo principal de la API.
    """
    global _canal

    # Adjuntar el request_id del contexto actual al evento.
    # Esto permite que el worker lea el ID al consumir y mantenga
    # la cadena de logs trazable a través de RabbitMQ.
    evento_con_traza = {**evento, "request_id": get_request_id()}

    try:
        await _canal.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(evento_con_traza).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=cola
        )
        log.info(f"Evento publicado en cola '{cola}'")
    except Exception as e:
        log.warning(f"No se pudo publicar evento en cola '{cola}': {e}")