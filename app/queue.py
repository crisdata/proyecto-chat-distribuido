# queue.py
# Gestiona la conexión a RabbitMQ y la publicación de eventos.
# Usa aio-pika para compatibilidad total con asyncio y FastAPI.
#
# El módulo expone dos funciones principales:
#   conectar_queue()  — crea la conexión al arrancar la aplicación
#   publicar()        — publica un evento en la cola especificada
#
# La cola 'mensajes' transporta eventos de mensajes enviados.
# El worker consume esa cola y actúa de forma desacoplada.

import aio_pika
import json
import os
from dotenv import load_dotenv

load_dotenv()

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

    # Declarar la cola como durable para que sobreviva reinicios
    # de RabbitMQ sin perder mensajes en tránsito
    await _canal.declare_queue("mensajes", durable=True)


async def desconectar_queue():
    """Cierra la conexión a RabbitMQ al apagar la aplicación."""
    global _conexion
    if _conexion:
        await _conexion.close()


async def publicar(cola: str, evento: dict):
    """
    Publica un evento JSON en la cola especificada.
    Si la conexión no está disponible, el error se registra
    pero no interrumpe el flujo principal de la API.
    """
    global _canal
    try:
        await _canal.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(evento).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=cola
        )
    except Exception as e:
        # RabbitMQ no disponible — el mensaje ya está en MariaDB,
        # solo se pierde la notificación asíncrona
        print(f"[queue] Error al publicar en {cola}: {e}")