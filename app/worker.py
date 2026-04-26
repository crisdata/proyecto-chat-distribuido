# worker.py
# Proceso independiente que consume eventos de la cola RabbitMQ.
# Se ejecuta en su propio contenedor Docker (chat_worker).
#
# Responsabilidades:
#   1. Consumir eventos de la cola "mensajes"
#   2. Llamar al endpoint interno de la API para notificar via WebSocket
#
# El worker no accede directamente a MariaDB ni al ConnectionManager
# porque la persistencia ya fue hecha por la API y el ConnectionManager
# vive en memoria del proceso FastAPI — no es accesible desde aquí.

import asyncio
import aio_pika
import json
import os
import aiohttp
from dotenv import load_dotenv

load_dotenv()

RABBITMQ_URL = (
    f"amqp://{os.getenv('RABBITMQ_USER', 'guest')}:"
    f"{os.getenv('RABBITMQ_PASSWORD', 'guest')}@"
    f"{os.getenv('RABBITMQ_HOST', 'rabbitmq')}:"
    f"{os.getenv('RABBITMQ_PORT', '5672')}/"
)

# URL interna de la API dentro de la red Docker
API_INTERNA_URL = os.getenv('API_INTERNA_URL', 'http://api:8000')


async def procesar_mensaje(message: aio_pika.IncomingMessage):
    """
    Procesa un evento de mensaje recibido de la cola.
    Llama al endpoint interno de la API para que notifique
    al receptor via WebSocket.
    """
    async with message.process():
        try:
            evento = json.loads(message.body.decode())

            receptor_id = evento.get("receptor_id")
            emisor_id = evento.get("emisor_id")
            emisor_nombre = evento.get("emisor_nombre")

            if not all([receptor_id, emisor_id, emisor_nombre]):
                print(f"[worker] Evento malformado: {evento}")
                return

            # Llamar al endpoint interno de la API para notificar
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{API_INTERNA_URL}/interno/notificar",
                    json={
                        "receptor_id": receptor_id,
                        "emisor_id": emisor_id,
                        "emisor_nombre": emisor_nombre
                    }
                ) as respuesta:
                    if respuesta.status == 200:
                        print(
                            f"[worker] Notificado: "
                            f"{emisor_nombre} → {receptor_id}"
                        )
                    else:
                        print(
                            f"[worker] Error al notificar: "
                            f"{respuesta.status}"
                        )

        except Exception as e:
            print(f"[worker] Error procesando mensaje: {e}")


async def main():
    """
    Punto de entrada del worker.
    Conecta a RabbitMQ y queda escuchando la cola indefinidamente.
    Usa connect_robust para reconectar automáticamente si RabbitMQ cae.
    """
    print("[worker] Iniciando...")

    conexion = await aio_pika.connect_robust(RABBITMQ_URL)
    canal = await conexion.channel()

    # Prefetch de 1: el worker procesa un mensaje a la vez
    # Garantiza que no se acumulen mensajes sin procesar
    await canal.set_qos(prefetch_count=1)

    cola = await canal.declare_queue("mensajes", durable=True)

    print("[worker] Escuchando cola 'mensajes'...")
    await cola.consume(procesar_mensaje)

    # Mantener el worker corriendo indefinidamente
    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())