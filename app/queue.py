# queue.py
# Gestiona la conexión a RabbitMQ y la publicación de eventos.
# Usa aio-pika para compatibilidad total con asyncio y FastAPI.
#
# Cada evento publicado incluye automáticamente el request_id de la
# petición HTTP en curso, permitiendo trazar el flujo del mensaje a
# través de la cola hasta el worker.

import asyncio
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

    Implementa reintentos con espera para tolerar arranques lentos del
    broker. En equipos modestos, RabbitMQ puede tomar 45+ segundos en
    estar listo para aceptar conexiones AMQP aunque el contenedor ya
    esté Up. Esta función no se rinde al primer fallo: intenta hasta 10
    veces con 3 segundos entre intentos.
    """
    global _conexion, _canal

    url = (
        f"amqp://{os.getenv('RABBITMQ_USER', 'guest')}:"
        f"{os.getenv('RABBITMQ_PASSWORD', 'guest')}@"
        f"{os.getenv('RABBITMQ_HOST', 'rabbitmq')}:"
        f"{os.getenv('RABBITMQ_PORT', '5672')}/"
    )

    intentos_maximos = 10
    espera_entre_intentos = 3  # segundos

    for intento in range(1, intentos_maximos + 1):
        try:
            log.info(
                f"Intento {intento}/{intentos_maximos} de conexión a RabbitMQ..."
            )
            _conexion = await aio_pika.connect_robust(url)
            _canal = await _conexion.channel()
            await _canal.declare_queue("mensajes", durable=True)
            log.info("Cola 'mensajes' declarada en RabbitMQ")
            return

        except Exception as e:
            if intento == intentos_maximos:
                log.error(
                    f"Imposible conectar a RabbitMQ tras "
                    f"{intentos_maximos} intentos. Último error: {e}"
                )
                raise RuntimeError(
                    f"No se pudo conectar a RabbitMQ tras {intentos_maximos} "
                    f"intentos. ¿El broker está corriendo?"
                ) from e

            log.warning(
                f"Intento {intento} falló ({type(e).__name__}: {e}). "
                f"Reintentando en {espera_entre_intentos}s..."
            )
            await asyncio.sleep(espera_entre_intentos)


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