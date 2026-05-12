# logging_config.py
# Configuración central de logging para toda la aplicación.
# Se llama una vez al arrancar desde main.py, antes de cualquier
# otra inicialización, para que todos los módulos hereden el formato.

import logging
import sys


def configurar_logging(nivel: int = logging.INFO):
    """
    Configura el logger raíz con formato consistente.
    Formato: timestamp - nivel - [componente] mensaje
    El componente se pasa al obtener el logger en cada módulo.
    """
    logging.basicConfig(
        level=nivel,
        format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        stream=sys.stdout,
        force=True,  # sobrescribe configuración previa de Uvicorn si la hubiera
    )

    # Reducir el ruido de librerías de terceros
    logging.getLogger("aio_pika").setLevel(logging.WARNING)
    logging.getLogger("aiormq").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)